from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from .models import Student
from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction


# For auth_views.py

# Replacing the email or the "identifier" with the students user name
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['identifier'] = self.fields.pop('username')
    
    def validate(self, attrs):
        identifier = attrs.get('username') or attrs.get('identifier')
        
        if "@" in identifier:# if a user used an email to sign in
            try:
                student = Student.objects.get(university_email=identifier)
                attrs['username'] = student.user.username
            except Student.DoesNotExist:
                    raise AuthenticationFailed("Invalid email or password.")
        else:
            attrs['username'] = identifier
        attrs.pop('identifier', None)

        return super().validate(attrs)


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['university_email', 'full_name', 'entry_year',
                'academic_level', 'department', 'cgpa', 'status']
        

class RegisterStudentSerializer(serializers.ModelSerializer):
    university_id = serializers.CharField(write_only=True)
    full_name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    entry_year = serializers.IntegerField(write_only=True, required=False)
    academic_level = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['university_id', 'full_name', 'email', 'password', 'entry_year', 'academic_level']
        
    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['university_id'],
                email=validated_data['email'],
                password=validated_data['password'],
                first_name=validated_data['full_name'] 
            )
            
            student = Student.objects.create(
                user=user,
                university_email=validated_data['email'],
                entry_year=validated_data.get('entry_year', 2026),
                academic_level=validated_data.get('academic_level', 1),
            )
        return user