from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from academics.engine import (
    student_plan, counted_attempts, passed_courses
)
from academics.models import (
    Semester, CourseOffering, StudentSemesterRecord, Enrollment,
    StudentCoursePreference, SavedGraduationPlan
)
from academics.pathfinder_adapter import recalculate_student_plan


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def curriculum_tree(request):
    """Tree 1: الخطة الدراسية الخاصة بالطالب مع الثلاث قنوات البصرية (الحالة، الترم، التفضيل)."""
    student = request.user.student
    current_sem = Semester.objects.filter(is_current=True).first()
    plan = student_plan(student)
    attempts = counted_attempts(student)
    passed = passed_courses(student)

    earned_hours = sum(
        plan[cid]['course'].credit_hours
        for cid in passed
        if cid in plan
    )

    registered = set()
    offered_this_sem = set()
    if current_sem:
        registered = set(
            Enrollment.objects.filter(
                student=student, status=Enrollment.Status.REGISTERED, offering__semester=current_sem
            ).values_list('offering__course_id', flat=True)
        )
        offered_this_sem = set(
            CourseOffering.objects.filter(
                semester=current_sem, status=CourseOffering.Status.OPEN
            ).values_list('course_id', flat=True)
        )

    prefs_map = dict(
        StudentCoursePreference.objects.filter(student=student)
        .values_list('course_id', 'kind')
    )

    nodes = []
    for cid, info in plan.items():
        course = info['course']
        prereqs = {}
        prereq_id_groups = {}
        for p in course.prerequisite_links.all():
            prereqs.setdefault(p.group, []).append(p.prerequisite.code)
            prereq_id_groups.setdefault(p.group, set()).add(p.prerequisite_id)

        unlocks = [u.course.code for u in course.unlocks_links.all()]

        prereqs_met = not prereq_id_groups or any(g <= passed for g in prereq_id_groups.values())
        level_met = student.academic_level >= course.min_level
        hours_met = earned_hours >= course.min_earned_hours

        lock_reason = None
        if cid in registered:
            status = 'registered'
        elif cid in passed:
            status = 'done'
        elif cid in attempts and attempts[cid].status == Enrollment.Status.FAILED:
            status = 'failed'
        elif not (prereqs_met and level_met and hours_met):
            status = 'locked'
            lock_reason = 'missing_prerequisites'
        else:
            # Prerequisites, level, and earned hours are all met; check term availability
            if current_sem and cid not in offered_this_sem:
                if current_sem.term == Semester.Term.SUMMER or course.typical_term not in (current_sem.term, 'both'):
                    status = 'locked'
                    lock_reason = 'wrong_term'
                else:
                    status = 'available'
            else:
                status = 'available'

        nodes.append({
            "code": course.code,
            "name": course.name,
            "name_ar": course.name_ar,
            "credits": course.credit_hours,
            "level": course.min_level,
            "min_earned_hours": course.min_earned_hours,
            "typical_term": course.typical_term,
            "requirement_group": info['group'],
            "requirement_type": info['type'],
            "preference": prefs_map.get(cid, "none"),
            "status": status,
            "lock_reason": lock_reason,
            "prerequisites": list(prereqs.values()),
            "unlocks": unlocks,
        })
    return Response(nodes)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def requirements_progress(request):
    """متطلبات التخرج وتتبع الإنجاز (144 ساعة)."""
    student = request.user.student
    plan = student_plan(student)
    attempts = counted_attempts(student)
    current_sem = Semester.objects.filter(is_current=True).first()

    registered_cids = []
    if current_sem:
        registered_cids = Enrollment.objects.filter(
            student=student, status='registered', offering__semester=current_sem
        ).values_list('offering__course_id', flat=True)

    progress = {
        "general": {"compulsory": {"earned": 0, "registered": 0, "required": 6}, "elective": {"earned": 0, "registered": 0, "required": 6}},
        "faculty": {"compulsory": {"earned": 0, "registered": 0, "required": 63}, "elective": {"earned": 0, "registered": 0, "required": 9}},
        "department": {"compulsory": {"earned": 0, "registered": 0, "required": 39}, "elective": {"earned": 0, "registered": 0, "required": 21}},
        "total_earned": 0,
        "total_required": 144,
    }

    if not student.department_id:
        progress["department"]["required"] = 0

    for cid, info in plan.items():
        grp = info['group']
        typ = info['type']
        hrs = info['course'].credit_hours

        if cid in attempts and attempts[cid].status == 'completed':
            progress[grp][typ]["earned"] += hrs
            progress["total_earned"] += hrs
        elif cid in registered_cids:
            progress[grp][typ]["registered"] += hrs

    return Response(progress)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def graduation_path(request):
    """مسار التخرج المحفوظ في SavedGraduationPlan (يعيد الحساب تلقائياً إذا كان is_stale=True)."""
    student = request.user.student
    saved_plan = SavedGraduationPlan.objects.filter(student=student).first()

    if (
        request.method == 'POST'
        or saved_plan is None
        or saved_plan.is_stale
        or not saved_plan.plan_data
    ):
        saved_plan = recalculate_student_plan(student)

    return Response(saved_plan.plan_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_history(request):
    """السجل الأكاديمي فصلاً بفصل."""
    records = StudentSemesterRecord.objects.filter(student=request.user.student).order_by('semester__start_date')
    history = []
    for r in records:
        enrollments = Enrollment.objects.filter(
            student=request.user.student, offering__semester=r.semester, status__in=['completed', 'failed']
        ).select_related('offering__course')

        courses = [{
            "code": e.offering.course.code,
            "name": e.offering.course.name,
            "score": e.score,
            "grade": e.grade_letter,
            "points": e.grade_points,
        } for e in enrollments]

        history.append({
            "semester": r.semester.label,
            "level_then": r.level_at_time,
            "semester_gpa": r.semester_gpa,
            "cumulative_gpa": r.cumulative_gpa,
            "credits_earned": r.credits_earned,
            "courses": courses,
        })
    return Response(history)