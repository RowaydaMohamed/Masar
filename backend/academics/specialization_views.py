from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Department, Course, DepartmentCourse
from .serializers import DepartmentSerializer


class SpecializationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        departments = Department.objects.filter(is_active=True).prefetch_related("degree_requirements")
        serializer = DepartmentSerializer(departments, many=True)
        return Response(serializer.data)


class SpecializationTreeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, code):
        department = get_object_or_404(Department, code__iexact=code, is_active=True)
        

        # General & Faculty courses (taken by all students)
        base_courses = Course.objects.filter(
            is_active=True,
            requirement_group__in=[Course.Group.GENERAL, Course.Group.FACULTY],
        ).prefetch_related("prerequisite_links__prerequisite", "unlocks_links__course")

        # department's Compulsory & Elective courses
        dept_links = DepartmentCourse.objects.filter(
            department=department,
            course__is_active=True,
        ).select_related("course").prefetch_related(
            "course__prerequisite_links__prerequisite",
            "course__unlocks_links__course",
        )

        # which department courses are shared with other departments
        shared_map = {}
        for role in DepartmentCourse.objects.select_related("department").all():
            shared_map.setdefault(role.course_id, []).append(role.department.code)


            items = [
            (c, c.requirement_group, c.requirement_type)
            for c in base_courses
        ] + [
            (dl.course, Course.Group.DEPARTMENT, dl.type)
            for dl in dept_links
        ]

        nodes = []
        for course, group, req_type in items:
            prereqs = {}
            for p in course.prerequisite_links.all():
                prereqs.setdefault(p.group, []).append(p.prerequisite.code)

            unlocks = [u.course.code for u in course.unlocks_links.all()]
            depts_using_course = shared_map.get(course.id, [])

            nodes.append({
                "code": course.code,
                "name": course.name,
                "name_ar": course.name_ar,
                "credits": course.credit_hours,
                "level": course.min_level,
                "semester": course.typical_term,
                "requirement_group": group,
                "requirement_type": req_type,
                "status": None,
                "is_shared": len(depts_using_course) > 1,
                "shared_with": depts_using_course,
                "prerequisites": list(prereqs.values()),
                "unlocks": unlocks,
            })

        return Response(nodes)