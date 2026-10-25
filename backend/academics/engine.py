from decimal import Decimal
from django.utils import timezone
from academics.models import (
    Course, Enrollment, LevelThreshold, Semester, CourseOffering,
    SystemSetting, DepartmentCourse, StudentCoursePreference
)

E = Enrollment.Status

def get_setting(key):
    DEFAULT_SETTINGS = {
        "max_courses_per_semester": 6,
        "seventh_course_min_cgpa": Decimal("3.00"),
        "summer_max_credits": 9,
        "graduation_min_cgpa": Decimal("2.00"),
        "probation_cgpa": Decimal("2.00"),
        "new_student_max_credits": 18,
    }
    default = DEFAULT_SETTINGS[key]
    row = SystemSetting.objects.filter(key=key).first()
    return type(default)(row.value) if row else default

def counted_attempts(student, up_to=None):
    """بيجيب آخر محاولة مسجلة للطالب (منتهية أو راسبة) لكل مادة وكدا."""
    qs = Enrollment.objects.filter(
        student=student, status__in=[E.COMPLETED, E.FAILED]
    ).select_related("offering__course", "offering__semester").order_by("offering__semester__start_date", "id")
    
    if up_to is not None:
        qs = qs.filter(offering__semester__start_date__lte=up_to.start_date)
        
    result = {}
    for e in qs:
        result[e.offering.course_id] = e
    return result

def student_plan(student):
    """بيرجع المواد الخاصة بخطة الطالب (عام، كلية، وقسمه إن وُجد)."""
    courses = list(Course.objects.filter(is_active=True, requirement_group__in=["general", "faculty"]))
    plan = {c.id: {'course': c, 'type': c.requirement_type, 'group': c.requirement_group} for c in courses}
    
    if student.department_id:
        dept_courses = DepartmentCourse.objects.filter(department=student.department).select_related('course')
        for dc in dept_courses:
            plan[dc.course_id] = {'course': dc.course, 'type': dc.type, 'group': 'department'}
            
    return plan

def passed_courses(student, up_to=None):
    """إرجاع الـ IDs للمواد التي اجتازها الطالب بنجاح."""
    attempts = counted_attempts(student, up_to)
    return {cid for cid, e in attempts.items() if e.status == E.COMPLETED}

def cgpa(student, up_to=None):
    """حساب المعدل التراكمي."""
    attempts = counted_attempts(student, up_to)
    num = Decimal(0)
    den = 0
    for e in attempts.values():
        h = e.offering.course.credit_hours
        num += e.grade_points * h
        den += h
    return (num / den).quantize(Decimal("0.01")) if den else None

def level_from_hours(hours):
    """تحديد المستوى الأكاديمي بناءً على الساعات المجتازة."""
    rows = LevelThreshold.objects.filter(min_earned_hours__lte=hours).order_by("-level")
    return rows.first().level if rows else 1

def standing(student, current_semester):
    """تحديد تصنيف الطالب (مستجد أم مستمر)."""
    lvl = student.academic_level
    if lvl == 1:
        fresh = current_semester.academic_year <= student.admission_semester.academic_year
        return f"سنة أولى {'مستجد' if fresh else 'مستمر'}"
    names = {2: "سنة ثانية", 3: "سنة ثالثة", 4: "سنة رابعة"}
    return names.get(lvl, f"سنة {lvl}")

def compute_course_statuses(student, current_semester):
    """حساب حالة كل مادة في الخطة بناءً على أولوية: مسجل -> مجتاز -> راسب -> متاح/مغلق."""
    plan = student_plan(student)
    attempts = counted_attempts(student)
    passed = passed_courses(student)
    
    registered = set(Enrollment.objects.filter(
        student=student, status=E.REGISTERED, offering__semester=current_semester
    ).values_list('offering__course_id', flat=True))
    
    avoid_prefs = set(StudentCoursePreference.objects.filter(
        student=student, kind='avoid'
    ).values_list('course_id', flat=True))

    offered_this_sem = set(CourseOffering.objects.filter(
        semester=current_semester, status='open'
    ).values_list('course_id', flat=True))

    statuses = {}
    for cid, info in plan.items():
        course = info['course']
        status = 'locked'
        
        # مراجعة المتطلبات السابقة
        groups = {}
        for link in course.prerequisite_links.all():
            groups.setdefault(link.group, set()).add(link.prerequisite_id)
        prereqs_met = not groups or any(g <= passed for g in groups.values())

        if cid in registered:
            status = 'registered'
        elif cid in passed:
            status = 'done'
        elif cid in attempts and attempts[cid].status == E.FAILED:
            status = 'failed'
        elif prereqs_met and student.academic_level >= course.min_level and cid in offered_this_sem:
            status = 'available'
            
        if status in ['available', 'locked'] and cid in avoid_prefs:
            status = 'avoid'
            
        statuses[cid] = status
    return statuses 
