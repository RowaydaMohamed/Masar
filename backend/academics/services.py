"""
academics/services.py

Engine helpers (read-only rules) + the four services that own multi-table writes:
    set_department, approve_seventh_request (+ reject), open_summer_offering, close_semester
Views and admin actions must call these and never write those tables directly.
"""

from django.db import transaction
from decimal import Decimal
from academics.models import Semester, Student, StudentSemesterRecord, Enrollment
from academics.engine import cgpa, counted_attempts, level_from_hours, student_plan
from django.db import transaction
from django.utils import timezone

from .models import (
    Course, CourseOffering, CreditLimitRule, DecisionStatus, DegreeRequirement, Department,
    DepartmentCourse, Enrollment, GradeScale, LevelThreshold, Notification, Semester,
    SeventhCourseRequest, Student, StudentDepartmentChange, StudentSemesterRecord,
    SummerRequest, SystemSetting, OfferingTimeSlot,
)

E = Enrollment.Status
_UNSET = object()


class DomainError(Exception):
    """A business rule was violated. Views turn this into HTTP 400/409."""


# ------------------------------------------------------------------ settings ----------
DEFAULT_SETTINGS = {                       # used when the SystemSetting row is missing
    "max_courses_per_semester": 6,
    "seventh_course_min_cgpa": Decimal("3.00"),      # PLACEHOLDER - ask the faculty
    "summer_max_credits": 9,                          # PLACEHOLDER
    "graduation_min_cgpa": Decimal("2.00"),
    "probation_cgpa": Decimal("2.00"),
    "new_student_max_credits": 18,                    # PLACEHOLDER (no CGPA yet)
}


def get_setting(key):
    default = DEFAULT_SETTINGS[key]
    row = SystemSetting.objects.filter(key=key).first()
    return type(default)(row.value) if row else default


# ------------------------------------------------------------------ engine ------------
def counted_attempts(student, up_to=None):
    """{course_id: Enrollment} - the latest graded (completed/failed) attempt per course.
    Withdrawn and registered rows are never counted. `up_to` = Semester (inclusive)."""
    qs = (Enrollment.objects
          .filter(student=student, status__in=[E.COMPLETED, E.FAILED])
          .select_related("offering__course", "offering__semester")
          .order_by("offering__semester__start_date", "id"))
    if up_to is not None:
        qs = qs.filter(offering__semester__start_date__lte=up_to.start_date)
    result = {}
    for e in qs:
        result[e.offering.course_id] = e          # later attempts overwrite earlier ones
    return result


def plan_course_ids(student, department=_UNSET):
    """Courses that count for this student: general + faculty + own department pool."""
    dept = student.department if department is _UNSET else department
    ids = set(Course.objects.filter(is_active=True,
                                    requirement_group__in=["general", "faculty"])
              .values_list("id", flat=True))
    if dept is not None:
        ids |= set(DepartmentCourse.objects.filter(department=dept).values_list("course_id", flat=True))
    return ids


def completed_hours(student, up_to=None, department=_UNSET):
    """Earned hours that count toward the 144 (passed + in plan)."""
    plan = plan_course_ids(student, department)
    return sum(e.offering.course.credit_hours
               for cid, e in counted_attempts(student, up_to).items()
               if e.status == E.COMPLETED and cid in plan)


def cgpa(student, up_to=None):
    """Credit-weighted over counted attempts (a failed counted attempt contributes 0 points).
    Out-of-plan grades stay in CGPA (default assumption). None if nothing graded."""
    num = Decimal(0)
    den = 0
    for e in counted_attempts(student, up_to).values():
        h = e.offering.course.credit_hours
        num += e.grade_points * h
        den += h
    return (num / den).quantize(Decimal("0.01")) if den else None


def level_for_hours(hours):
    rows = LevelThreshold.objects.filter(min_earned_hours__lte=hours).order_by("-level")
    return rows.first().level if rows else 1


def level_label(student, current_semester):
    """Computed, never stored. Level 1: 'مستجد' during the admission academic year, else 'مستمر'."""
    names = {1: "سنة أولى", 2: "سنة ثانية", 3: "سنة ثالثة", 4: "سنة رابعة"}
    lvl = student.academic_level
    if lvl == 1:
        fresh = current_semester.academic_year <= student.admission_semester.academic_year
        return f"{names[1]} {'مستجد' if fresh else 'مستمر'}"
    return names[lvl]


def required_hours(department):
    """144 for a student in `department` (general + faculty + dept rows)."""
    from django.db.models import Q, Sum
    q = Q(department__isnull=True)
    if department is not None:
        q |= Q(department=department)
    return DegreeRequirement.objects.filter(q).aggregate(s=Sum("required_hours"))["s"] or 0


def department_at(student, semester):
    ch = (StudentDepartmentChange.objects
          .filter(student=student, semester__start_date__lte=semester.start_date)
          .select_related("to_department")
          .order_by("semester__start_date", "changed_at", "id").last())
    return ch.to_department if ch else None


def max_credits_for(student, semester):
    if semester.term == Semester.Term.SUMMER:
        return get_setting("summer_max_credits")
    g = cgpa(student)
    if g is None:
        return get_setting("new_student_max_credits")
    for r in CreditLimitRule.objects.all():
        if (r.min_cgpa is None or g >= r.min_cgpa) and (r.max_cgpa is None or g < r.max_cgpa):
            return r.max_credits
    return get_setting("new_student_max_credits")


def registered_in(student, semester):
    return list(Enrollment.objects
                .filter(student=student, status=E.REGISTERED, offering__semester=semester)
                .select_related("offering__course").prefetch_related("offering__time_slots"))


def _overlaps(slots_a, slots_b):
    return any(a.day == b.day and a.start_time < b.end_time and b.start_time < a.end_time
               for a in slots_a for b in slots_b)


def can_register(student, offering, *, admin_override=False):
    """-> list of reason codes; an empty list means the student may register.
    admin_override (7th-course approval) skips the deadline, course-count and credit limits."""
    reasons = []
    course, sem = offering.course, offering.semester
    if student.status != Student.Status.ACTIVE:
        reasons.append("student_not_active")
    if offering.status != CourseOffering.Status.OPEN:
        reasons.append("offering_not_open")
    if sem.is_closed:
        reasons.append("semester_closed")
    if not admin_override and timezone.now() > sem.registration_deadline:
        reasons.append("registration_deadline_passed")
    if not course.is_active or course.id not in plan_course_ids(student):
        reasons.append("outside_plan")
    counted = counted_attempts(student)
    passed = {cid for cid, e in counted.items() if e.status == E.COMPLETED}
    if course.id in passed:
        reasons.append("already_passed")                    # no grade-improvement retakes
    if Enrollment.objects.filter(student=student, status=E.REGISTERED, offering__course=course).exists():
        reasons.append("already_registered")
    if student.academic_level < course.min_level:
        reasons.append("level_too_low")
    groups = {}
    for link in course.prerequisite_links.all():
        groups.setdefault(link.group, set()).add(link.prerequisite_id)
    if groups and not any(g <= passed for g in groups.values()):   # AND in group, OR across
        reasons.append("prerequisites_not_met")
    if offering.capacity is not None and offering.enrollments.filter(status=E.REGISTERED).count() >= offering.capacity:
        reasons.append("offering_full")
    current = registered_in(student, sem)
    if not admin_override:
        if len(current) >= get_setting("max_courses_per_semester"):
            reasons.append("course_limit_reached")
        if sum(e.offering.course.credit_hours for e in current) + course.credit_hours > max_credits_for(student, sem):
            reasons.append("credit_limit_exceeded")
    new_slots = list(offering.time_slots.all())
    if any(_overlaps(new_slots, list(e.offering.time_slots.all())) for e in current):
        reasons.append("time_conflict")
    return reasons


# ------------------------------------------------------------------ helpers -----------
def notify(student, type_, text, text_ar="", link=""):
    return Notification.objects.create(student=student, type=type_, text=text, text_ar=text_ar, link=link)


def current_semester():
    s = Semester.objects.filter(is_current=True).first()
    if not s:
        raise DomainError("No current semester is configured.")
    return s


# ------------------------------------------------------------------ registration ------
@transaction.atomic
def register_course(student, offering, *, admin_override=False):
    reasons = can_register(student, offering, admin_override=admin_override)
    if reasons:
        raise DomainError(", ".join(reasons))
    # unique(student, offering): re-use a withdrawn row instead of inserting a duplicate
    e, created = Enrollment.objects.get_or_create(student=student, offering=offering,
                                                  defaults={"status": E.REGISTERED})
    if not created:
        e.status = E.REGISTERED
        e.save(update_fields=["status", "updated_at"])
    return e


@transaction.atomic
def withdraw_course(enrollment):
    if enrollment.status != E.REGISTERED:
        raise DomainError("Only a registered course can be withdrawn.")
    enrollment.status = E.WITHDRAWN
    enrollment.save(update_fields=["status", "updated_at"])
    return enrollment


@transaction.atomic
def post_grade(enrollment, score, graded_by=None):
    """Posts a score: picks the letter from GradeScale and COPIES letter/points (snapshot)."""
    enrollment = Enrollment.objects.select_for_update().get(pk=enrollment.pk)
    if enrollment.status != E.REGISTERED:
        raise DomainError("Only registered enrollments can be graded.")
    if enrollment.offering.semester.is_closed:
        raise DomainError("Semester is closed.")
    score = Decimal(score)
    gs = GradeScale.objects.filter(min_score__lte=score).order_by("-min_score").first()
    if gs is None:
        raise DomainError("GradeScale is not configured for this score.")
    enrollment.score, enrollment.grade_letter, enrollment.grade_points = score, gs.letter, gs.points
    enrollment.status = E.COMPLETED if gs.is_passing else E.FAILED
    enrollment.graded_by, enrollment.graded_at = graded_by, timezone.now()
    enrollment.save()
    return enrollment


# ------------------------------------------------------------------ SERVICE 1 ---------
@transaction.atomic
def set_department(student, department):
    student = Student.objects.select_for_update().get(pk=student.pk)
    if not department.is_active:
        raise DomainError("Department is not active.")
    if student.department_id == department.id:
        return student
    # TODO(doctor): restrict by level once the rule is known.
    StudentDepartmentChange.objects.create(
        student=student, from_department=student.department, to_department=department,
        semester=current_semester())
    student.department = department
    student.save(update_fields=["department", "updated_at"])
    notify(student, Notification.Type.DEPARTMENT_CHANGED,
           f"Your department is now {department.code}.", f"تم تغيير قسمك إلى {department.code}.",
           "/graduation-path")
    return student


# ------------------------------------------------------------------ 7th course --------
def seventh_course_eligibility(student, semester):
    """-> (eligible, reasons). The UI shows the button only when eligible."""
    reasons = []
    if len(registered_in(student, semester)) < get_setting("max_courses_per_semester"):
        reasons.append("below_course_limit")                # just register normally
    g = cgpa(student)
    if g is None or g < get_setting("seventh_course_min_cgpa"):
        reasons.append("cgpa_below_minimum")
    if SeventhCourseRequest.objects.filter(student=student, status=DecisionStatus.PENDING,
                                           offering__semester=semester).exists():
        reasons.append("pending_request_exists")
    return (not reasons), reasons


@transaction.atomic
def submit_seventh_request(student, offering, reason=""):
    ok, reasons = seventh_course_eligibility(student, offering.semester)
    if not ok:
        raise DomainError(", ".join(reasons))
    blockers = can_register(student, offering, admin_override=True)
    if blockers:
        raise DomainError(", ".join(blockers))
    return SeventhCourseRequest.objects.create(student=student, offering=offering, reason=reason)


@transaction.atomic
def approve_seventh_request(req, decided_by, decision_reason=""):
    """request status + Enrollment + Notification, atomically."""
    req = SeventhCourseRequest.objects.select_for_update().select_related(
        "student", "offering__course", "offering__semester").get(pk=req.pk)
    if req.status != DecisionStatus.PENDING:
        raise DomainError("Request was already decided.")
    if req.offering.status != CourseOffering.Status.OPEN:
        raise DomainError("The offering is no longer open.")
    register_course(req.student, req.offering, admin_override=True)
    req.status, req.decided_by, req.decided_at = DecisionStatus.APPROVED, decided_by, timezone.now()
    req.decision_reason = decision_reason
    req.save()
    notify(req.student, Notification.Type.SEVENTH_APPROVED,
           f"Your 7th course request for {req.offering.course.code} was approved.",
           f"تمت الموافقة على طلب المادة السابعة {req.offering.course.code}.", "/curriculum")
    return req


@transaction.atomic
def reject_seventh_request(req, decided_by, decision_reason=""):
    req = SeventhCourseRequest.objects.select_for_update().select_related(
        "student", "offering__course").get(pk=req.pk)
    if req.status != DecisionStatus.PENDING:
        raise DomainError("Request was already decided.")
    req.status, req.decided_by, req.decided_at = DecisionStatus.REJECTED, decided_by, timezone.now()
    req.decision_reason = decision_reason
    req.save()
    notify(req.student, Notification.Type.SEVENTH_REJECTED,
           f"Your 7th course request for {req.offering.course.code} was rejected.",
           f"تم رفض طلب المادة السابعة {req.offering.course.code}.", "/curriculum")
    return req


# ------------------------------------------------------------------ summer ------------
@transaction.atomic
def submit_summer_requests(student, courses, semester):
    if semester.term != Semester.Term.SUMMER:
        raise DomainError("Summer requests need a summer semester.")
    plan = plan_course_ids(student)
    passed = {cid for cid, e in counted_attempts(student).items() if e.status == E.COMPLETED}
    out = []
    for c in courses:
        if c.id not in plan or c.id in passed:
            raise DomainError(f"{c.code} is not eligible for summer demand.")
        out.append(SummerRequest.objects.get_or_create(student=student, course=c, semester=semester)[0])
    return out


# ------------------------------------------------------------------ SERVICE 3 ---------
@transaction.atomic
def open_summer_offering(course, semester, decided_by, instructor=None, slots=()):
    """slots: iterable of (day, start_time, end_time). Creates/opens the offering, links the
    pending requests, notifies the students."""
    if semester.term != Semester.Term.SUMMER:
        raise DomainError("Not a summer semester.")
    offering, _ = CourseOffering.objects.get_or_create(course=course, semester=semester)
    offering.status, offering.instructor = CourseOffering.Status.OPEN, instructor or offering.instructor
    offering.save()
    for day, start, end in slots:
        OfferingTimeSlot.objects.get_or_create(offering=offering, day=day, start_time=start,
                                               defaults={"end_time": end})
    now = timezone.now()
    pending = list(SummerRequest.objects.select_for_update().select_related("student")
                   .filter(course=course, semester=semester, status=DecisionStatus.PENDING))
    for r in pending:
        r.status, r.fulfilled_by_offering = DecisionStatus.APPROVED, offering
        r.decided_by, r.decided_at = decided_by, now
        r.save()
    Notification.objects.bulk_create([
        Notification(student=r.student, type=Notification.Type.SUMMER_OPENED,
                     text=f"{course.code} will be offered in summer. Register now.",
                     text_ar=f"تم فتح مادة {course.code} في الصيفي. سجّل الآن.", link="/summer")
        for r in pending])
    return offering, len(pending)


@transaction.atomic
def reject_summer_demand(course, semester, decided_by, reason=""):
    now = timezone.now()
    pending = list(SummerRequest.objects.select_related("student").filter(
        course=course, semester=semester, status=DecisionStatus.PENDING))
    for r in pending:
        r.status, r.decided_by, r.decided_at, r.decision_reason = DecisionStatus.REJECTED, decided_by, now, reason
        r.save()
    Notification.objects.bulk_create([
        Notification(student=r.student, type=Notification.Type.SUMMER_REJECTED,
                     text=f"{course.code} will not be offered in summer.",
                     text_ar=f"لن يتم فتح مادة {course.code} في الصيفي.", link="/summer") for r in pending])
    return len(pending)


# ------------------------------------------------------------------ SERVICE 4 ---------
@transaction.atomic
def close_semester(semester):
    """Freezes one StudentSemesterRecord per student and writes Student.academic_level."""
    if semester.is_closed:
        raise DomainError("Semester already closed.")
    if Enrollment.objects.filter(offering__semester=semester, status=E.REGISTERED).exists():
        raise DomainError("Ungraded (registered) enrollments remain in this semester.")
    ids = (Enrollment.objects.filter(offering__semester=semester)
           .exclude(status=E.WITHDRAWN).values_list("student_id", flat=True).distinct())
    for student in Student.objects.select_for_update().filter(id__in=list(ids)):
        rows = list(Enrollment.objects.filter(student=student, offering__semester=semester,
                                              status__in=[E.COMPLETED, E.FAILED])
                    .select_related("offering__course"))
        attempted = sum(r.offering.course.credit_hours for r in rows)
        earned = sum(r.offering.course.credit_hours for r in rows if r.status == E.COMPLETED)
        pts = sum(r.grade_points * r.offering.course.credit_hours for r in rows)
        sem_gpa = (pts / attempted).quantize(Decimal("0.01")) if attempted else Decimal("0.00")
        dept = department_at(student, semester)
        hours = completed_hours(student, up_to=semester, department=dept)
        level = level_for_hours(hours)
        StudentSemesterRecord.objects.create(
            student=student, semester=semester, level_at_time=level, department_at_time=dept,
            credits_attempted=attempted, credits_earned=earned, cumulative_earned_hours=hours,
            semester_gpa=sem_gpa, cumulative_gpa=cgpa(student, up_to=semester) or Decimal("0.00"))
        student.academic_level = level
        student.save(update_fields=["academic_level", "updated_at"])
    semester.is_closed, semester.is_current = True, False
    semester.save(update_fields=["is_closed", "is_current"])



class DomainError(Exception):
    pass

def close_semester(semester: Semester):
    """
    إغلاق الترم الحالي:
    1. التأكد من أنه الترم الحالي.
    2. حساب المعدل الفصلي والتراكمي لكل طالب مسجل.
    3. تسجيل Snapshot (StudentSemesterRecord).
    4. ترقية المستوى الأكاديمي للطالب بناءً على ساعاته المجتازة.
    5. تغيير حالة الترم إلى مغلق (is_current = False).
    """
    if not semester.is_current:
        raise DomainError("لا يمكن إغلاق هذا الترم لأنه ليس الترم الحالي.")

    with transaction.atomic():
        # جلب كل الطلاب الذين لديهم تسجيلات في هذا الترم
        students = Student.objects.filter(enrollments__offering__semester=semester).distinct()

        for student in students:
            # 1. حساب المعدل الفصلي (Semester GPA)
            term_enrollments = Enrollment.objects.filter(
                student=student,
                offering__semester=semester,
                status__in=[Enrollment.Status.COMPLETED, Enrollment.Status.FAILED]
            ).select_related('offering__course')

            term_points = Decimal(0)
            term_hours = 0
            
            for e in term_enrollments:
                h = e.offering.course.credit_hours
                term_points += e.grade_points * h
                term_hours += h
                
            term_gpa = (term_points / term_hours).quantize(Decimal("0.01")) if term_hours > 0 else Decimal(0)

            # 2. حساب الساعات المجتازة الكلية من خطة الطالب
            plan = student_plan(student)
            attempts = counted_attempts(student, up_to=semester)
            
            total_earned_hours = sum(
                info['course'].credit_hours 
                for cid, info in plan.items() 
                if cid in attempts and attempts[cid].status == Enrollment.Status.COMPLETED
            )

            # 3. حساب المعدل التراكمي (CGPA)
            current_cgpa = cgpa(student, up_to=semester) or Decimal(0)

            # 4. إنشاء الـ Record (السجل)
            StudentSemesterRecord.objects.create(
                student=student,
                semester=semester,
                level_at_time=student.academic_level,
                semester_gpa=term_gpa,
                cumulative_gpa=current_cgpa,
                credits_earned=total_earned_hours
            )

            # 5. تحديث مستوى الطالب الأكاديمي
            new_level = level_from_hours(total_earned_hours)
            if new_level > student.academic_level:
                student.academic_level = new_level
                student.save(update_fields=['academic_level'])

        # أخيرًا: إغلاق الترم
        semester.is_current = False
        semester.save(update_fields=['is_current'])