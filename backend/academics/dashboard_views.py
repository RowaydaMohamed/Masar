# academics/dashboard_views.py

from django.conf import settings
from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from academics.models import (
    StudentCourseHistory,
    ScheduleSlot,
    Notification,
    SummerRequest,
    SeventhCourseRequest,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    student = request.user.student  # Ammar's Student <-> User link

    # ---- completed hours + graduation progress: computed live, not cached ----
    # (Student.total_hours_completed exists as a field too — decide with the
    # team whether that's meant to be kept in sync elsewhere, or whether this
    # live aggregate should be the single source of truth. Using the live
    # aggregate here either way, since the sprint doc explicitly asks for that.)
    completed_hours = (
        StudentCourseHistory.objects
        .filter(student=student, status='completed')
        .aggregate(total=Sum('course__credit_hours'))['total'] or 0
    )

    # TODO: confirm — global constant (132) or per-department? see note above.
    required_hours = getattr(settings, 'TOTAL_GRADUATION_HOURS', 132)

    graduation_progress_pct = (
        round((completed_hours / required_hours) * 100) if required_hours else 0
    )

    registered_qs = (
        StudentCourseHistory.objects
        .filter(student=student, status='registered')
        .select_related('course')
    )

    registered_courses = [
        {"code": h.course.code, "name": h.course.name_ar, "hours": h.course.credit_hours}
        for h in registered_qs
    ]

    profile = {
        "full_name": student.full_name,
        "specialization": student.department.name_ar if student.department else None,
        "academic_level": student.academic_level,
        "cgpa": float(student.cgpa),
        "completed_hours": completed_hours,
        "required_hours": required_hours,
        "graduation_progress_pct": graduation_progress_pct,
        "registered_count": registered_qs.count(),
    }

    schedule = [
        {
            "day": s.day,
            "start": s.start_time.strftime("%H:%M"),
            "end": s.end_time.strftime("%H:%M"),
            "course_code": s.course.code,
        }
        for s in ScheduleSlot.objects.filter(student=student).select_related('course')
    ]

    summer_requests = [
        {"course_code": r.course.code, "course_name": r.course.name_ar, "status": r.status}
        for r in SummerRequest.objects.filter(student=student).select_related('course')
    ]

    seventh = (
        SeventhCourseRequest.objects
        .filter(student=student)
        .select_related('course')
        .order_by('-requested_at')
        .first()
    )
    seventh_course_request = (
        {"course_code": seventh.course.code, "course_name": seventh.course.name_ar, "status": seventh.status}
        if seventh else None
    )

    notifications = [
        {"icon": n.icon, "text": n.text, "time": n.created_at.isoformat()}
        for n in Notification.objects.filter(student=student).order_by('-created_at')[:5]
    ]

    # TODO: no RegistrationDeadline model/constant exists yet — see note above.
    registration_deadline = getattr(
        settings, 'REGISTRATION_DEADLINE', "2026-09-20T23:59:00"
    )

    return Response({
        "profile": profile,
        "registered_courses": registered_courses,
        "schedule": schedule,
        "registration_deadline": registration_deadline,
        "summer_requests": summer_requests,
        "seventh_course_request": seventh_course_request,
        "notifications": notifications,
    })