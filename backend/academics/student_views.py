from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Course, Department, StudentCoursePreference
from .pathfinder_adapter import is_course_compulsory_for_student


class UpdateSpecializationView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        code = request.data.get("department_code")
        if not code:
            return Response(
                {"error": "department_code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        department = get_object_or_404(Department, code__iexact=code, is_active=True)
        student = request.user.student

        try:
            services.set_department(student, department)
            return Response(
                {"message": f"Specialization updated to {department.code} successfully."}
            )
        except services.DomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StudentPreferencesView(APIView):
    """GET & PUT /api/me/preferences/ with compulsory Avoid guardrail and plan recalculation."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = request.user.student
        prefs = (
            StudentCoursePreference.objects.filter(student=student)
            .select_related("course")
            .order_by("course__code")
        )
        return Response([
            {
                "course_code": p.course.code,
                "course_name": p.course.name,
                "course_name_ar": p.course.name_ar,
                "kind": p.kind,
            }
            for p in prefs
        ])

    def put(self, request):
        student = request.user.student

        if isinstance(request.data, list):
            items = request.data
        elif isinstance(request.data, dict) and "preferences" in request.data:
            items = request.data.get("preferences")
        else:
            items = [request.data]

        if not isinstance(items, list) or not items:
            return Response(
                {"error": "Provide course_code and kind ('want', 'avoid', or 'none')."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resolved_ops = []
        for item in items:
            if not isinstance(item, dict):
                return Response(
                    {"error": "Each preference entry must be an object."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            code = item.get("course_code") or item.get("code")
            course_id = item.get("course_id")
            raw_kind = item.get("kind")
            kind = raw_kind.lower().strip() if isinstance(raw_kind, str) else raw_kind

            if not code and not course_id:
                return Response(
                    {"error": "course_code is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if kind not in ("want", "avoid", "none", None, ""):
                return Response(
                    {"error": "kind must be 'want', 'avoid', or 'none'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            course = (
                get_object_or_404(Course, code__iexact=code, is_active=True)
                if code
                else get_object_or_404(Course, pk=course_id, is_active=True)
            )

            # Guardrail: Compulsory courses cannot be marked Avoid
            if kind == "avoid" and is_course_compulsory_for_student(student, course):
                return Response(
                    {
                        "error": f"Course {course.code} is compulsory and cannot be marked as 'avoid'.",
                        "course_code": course.code,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            resolved_ops.append((course, kind))

        with transaction.atomic():
            for course, kind in resolved_ops:
                if kind in ("none", None, ""):
                    StudentCoursePreference.objects.filter(
                        student=student, course=course
                    ).delete()
                else:
                    StudentCoursePreference.objects.update_or_create(
                        student=student,
                        course=course,
                        defaults={"kind": kind},
                    )
            services.trigger_plan_recalculation(student)

        updated_prefs = (
            StudentCoursePreference.objects.filter(student=student)
            .select_related("course")
            .order_by("course__code")
        )
        return Response({
            "message": "Preferences updated successfully.",
            "preferences": [
                {
                    "course_code": p.course.code,
                    "kind": p.kind,
                }
                for p in updated_prefs
            ],
        })