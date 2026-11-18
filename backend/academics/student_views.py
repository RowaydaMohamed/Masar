from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Department
from . import services

class UpdateSpecializationView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        code = request.data.get("department_code")
        if not code:
            return Response(
                {"error": "department_code is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        department = get_object_or_404(Department, code__iexact=code, is_active=True)
        student = request.user.student

        try:
            services.set_department(student, department)
            return Response({"message": f"Specialization updated to {department.code} successfully."})
            
        except services.DomainError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        