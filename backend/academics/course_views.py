from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Course, Semester
from .engine import compute_course_statuses

class CourseDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, code):
        course = get_object_or_404(Course, code__iexact=code, is_active=True)
        student = request.user.student
        current_sem = Semester.objects.filter(is_current=True).first()
        statuses = compute_course_statuses(student, current_sem)
        personal_status = statuses.get(course.id, "locked")
        
        prereqs = {}
        for p in course.prerequisite_links.all():
            prereqs.setdefault(p.group, []).append(p.prerequisite.code)

        unlocks = [u.course.code for u in course.unlocks_links.all()]
        
        return Response({
            "code": course.code,
            "name": course.name,
            "name_ar": course.name_ar,
            "description": course.description,
            "description_ar": course.description_ar,
            "credits": course.credit_hours,
            "level": course.min_level,
            "status": personal_status,
            "prerequisites": list(prereqs.values()),
            "unlocks": unlocks,
        })