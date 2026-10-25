from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Department
from .serializers import DepartmentSerializer


class SpecializationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        departments = Department.objects.filter(is_active=True). prefetch_related("degree_requirements")
        serializer = DepartmentSerializer(departments, many=True)
        return Response(serializer.data)