from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import CourseOffering
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