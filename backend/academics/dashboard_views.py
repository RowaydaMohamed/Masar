# academics/dashboard_views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from academics import services
from academics.models import (
    Enrollment,
    Notification,
    OfferingTimeSlot,
    Semester,
    SeventhCourseRequest,
    SummerRequest,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    # The authenticated user's Student profile.
    student = request.user.student

    # Current semester may not have been configured yet.
    current_semester = Semester.objects.filter(is_current=True).first()

    # ---------------------------------------------------------
    # Graduation progress and academic profile
    # ---------------------------------------------------------
    completed_hours = services.completed_hours(student)

    # The current bylaw defines a 144-credit-hour degree.
    required_hours = 144

    graduation_progress_pct = (
        round((completed_hours / required_hours) * 100)
        if required_hours
        else 0
    )

    student_cgpa = services.cgpa(student)

    # ---------------------------------------------------------
    # Currently registered courses
    # ---------------------------------------------------------
    registered_qs = Enrollment.objects.filter(
        student=student,
        status=Enrollment.Status.REGISTERED,
    )

    if current_semester:
        registered_qs = registered_qs.filter(
            offering__semester=current_semester
        )
    else:
        registered_qs = registered_qs.none()

    registered_qs = registered_qs.select_related(
        "offering__course",
        "offering__semester",
    ).order_by("offering__course__code")

    registered_courses = [
        {
            "code": enrollment.offering.course.code,
            "name": (
                enrollment.offering.course.name_ar
                or enrollment.offering.course.name
            ),
            "hours": enrollment.offering.course.credit_hours,
        }
        for enrollment in registered_qs
    ]

    profile = {
        "full_name": student.full_name,
        "specialization": (
            (
                student.department.name_ar
                or student.department.name
            )
            if student.department
            else None
        ),
        "academic_level": student.academic_level,
        "cgpa": float(student_cgpa or 0),
        "completed_hours": completed_hours,
        "required_hours": required_hours,
        "graduation_progress_pct": graduation_progress_pct,
        "registered_count": len(registered_courses),
    }

    # ---------------------------------------------------------
    # Weekly schedule for the student's registered courses
    # ---------------------------------------------------------
    if current_semester:
        schedule_qs = (
            OfferingTimeSlot.objects.filter(
                offering__semester=current_semester,
                offering__enrollments__student=student,
                offering__enrollments__status=Enrollment.Status.REGISTERED,
            )
            .select_related("offering__course")
            .distinct()
            .order_by("day", "start_time")
        )
    else:
        schedule_qs = OfferingTimeSlot.objects.none()

    schedule = [
        {
            "day": slot.day,
            "start": slot.start_time.strftime("%H:%M"),
            "end": slot.end_time.strftime("%H:%M"),
            "course_code": slot.offering.course.code,
            "course_name": (
                slot.offering.course.name_ar
                or slot.offering.course.name
            ),
        }
        for slot in schedule_qs
    ]

    # ---------------------------------------------------------
    # Summer requests
    # ---------------------------------------------------------
    summer_qs = SummerRequest.objects.filter(
        student=student
    ).select_related("course", "semester").order_by("-created_at")

    summer_requests = [
        {
            "course_code": request.course.code,
            "course_name": request.course.name_ar or request.course.name,
            "status": request.status,
            "semester": request.semester.label,
        }
        for request in summer_qs
    ]

    # ---------------------------------------------------------
    # Seventh-course request
    # ---------------------------------------------------------
    seventh = (
        SeventhCourseRequest.objects.filter(student=student)
        .select_related("offering__course", "offering__semester")
        .order_by("-created_at")
        .first()
    )

    seventh_course_request = (
        {
            "course_code": seventh.offering.course.code,
            "course_name": (
                seventh.offering.course.name_ar
                or seventh.offering.course.name
            ),
            "status": seventh.status,
            "created_at": seventh.created_at.isoformat(),
        }
        if seventh
        else None
    )

    # ---------------------------------------------------------
    # Latest notifications
    # ---------------------------------------------------------
    notification_icons = {
        NotificationType: icon
        for NotificationType, icon in [
            ("seventh_approved", "check-circle"),
            ("seventh_rejected", "x-circle"),
            ("summer_opened", "book-open"),
            ("summer_rejected", "x-circle"),
            ("department_changed", "git-branch"),
            ("system", "bell"),
        ]
    }

    notifications = [
        {
            "icon": notification_icons.get(notification.type, "bell"),
            "type": notification.type,
            "text": notification.text_ar or notification.text,
            "time": notification.created_at.isoformat(),
            "is_read": notification.is_read,
        }
        for notification in Notification.objects.filter(
            student=student
        ).order_by("-created_at")[:5]
    ]

    # ---------------------------------------------------------
    # Registration deadline
    # ---------------------------------------------------------
    registration_deadline = (
        current_semester.registration_deadline.isoformat()
        if current_semester
        else None
    )

    return Response(
        {
            "profile": profile,
            "registered_courses": registered_courses,
            "schedule": schedule,
            "registration_deadline": registration_deadline,
            "summer_requests": summer_requests,
            "seventh_course_request": seventh_course_request,
            "notifications": notifications,
        }
    )
