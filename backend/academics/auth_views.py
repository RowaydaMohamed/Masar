from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer, StudentSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Student
from rest_framework import generics
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
from .serializers import RegisterStudentSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        student = Student.objects.get(user=request.user)
        serializer = StudentSerializer(student)
        
        return Response(serializer.data)
    
class RegisterStudentView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny] # will be changed when an admin user is created
    serializer_class = RegisterStudentSerializer