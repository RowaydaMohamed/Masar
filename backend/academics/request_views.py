from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import CourseOffering, Course, SummerRequest
from .engine import student_plan, passed_courses
from . import services

class SubmitSeventhRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        course_code = request.data.get("course_code")
        reason = request.data.get("reason", "")

        if not course_code:
            return Response(
                {"error": "course_code is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            current_sem = services.current_semester()
            offering = get_object_or_404(
                CourseOffering,
                course__code__iexact=course_code,
                semester=current_sem,
                status='open'
            )
            services.submit_seventh_request(request.user.student, offering, reason)
            return Response(
                {"message": "7th course request submitted successfully."},
                status=status.HTTP_201_CREATED
            )
            
        except services.DomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class SubmitSummerRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = request.user.student
        
        plan = student_plan(student)
        passed_cids = passed_courses(student)
        
        eligible_courses = []
        for cid, info in plan.items():
            if cid not in passed_cids:
                course = info['course']
                eligible_courses.append({
                    "code": course.code,
                    "name": course.name,
                    "name_ar": course.name_ar,
                    "credits": course.credit_hours
                })
        
        try:
            current_sem = services.current_semester()
            existing_requests = SummerRequest.objects.filter(
                student=student, 
                semester=current_sem
            ).values_list("course__code", flat=True)
        except services.DomainError:
            existing_requests = []

        return Response({
            "eligible_courses": eligible_courses,
            "existing_requests": list(existing_requests)
        })

    def post(self, request):
        course_codes = request.data.get("course_codes", [])
        
        if not course_codes or not isinstance(course_codes, list):
            return Response(
                {"error": "A list of course_codes is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            current_sem = services.current_semester()
            
            # to get all matching courses from the database
            codes_upper = [code.upper() for code in course_codes]
            courses = list(Course.objects.filter(code__in=codes_upper, is_active=True))
            
            if len(courses) != len(course_codes):
                return Response(
                    {"error": "One or more course codes are invalid or inactive."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            services.submit_summer_requests(request.user.student, courses, current_sem)
            
            return Response(
                {"message": "Summer requests submitted successfully."},
                status=status.HTTP_201_CREATED
            )
            
        except services.DomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)