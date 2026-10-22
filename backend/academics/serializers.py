from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from .models import Student, Semester
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
                user = User.objects.get(email=identifier)
                attrs['username'] = user.username
            except User.DoesNotExist:
                    raise AuthenticationFailed("Invalid email or password.")
        else:
            attrs['username'] = identifier
        attrs.pop('identifier', None)

        return super().validate(attrs)


class StudentSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    department = serializers.SerializerMethodField()
    standing = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'university_id', 'email', 'full_name', 'full_name_ar',
            'academic_level', 'department', 'standing', 'status'
            
        ]

    def get_department(self, obj):
        if obj.department:
            return {
                "code": obj.department.code,
                "name": obj.department.name,
                "name_ar": obj.department.name_ar,
            }
        return None

    def get_standing(self, obj):
        try:
            from .engine import standing
            return standing(obj)
        except ImportError:
            return "new" if obj.academic_level == 1 else "continuing"

class RegisterStudentSerializer(serializers.ModelSerializer):
    university_id = serializers.CharField(write_only=True)
    full_name = serializers.CharField(write_only=True)
    full_name_ar = serializers.CharField(write_only=True, required=False, default="")
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    academic_level = serializers.IntegerField(write_only=True, required=False, default=1)
    admission_semester_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['university_id', 'full_name', 'full_name_ar', 'email',
                'password', 'academic_level', 'admission_semester_id']
        
    def create(self, validated_data):
        semester_id = validated_data.get('admission_semester_id')
        if semester_id:
            semester = Semester.objects.filter(id=semester_id).first()
        else:
            semester = Semester.objects.filter(is_current=True).first() or Semester.objects.first()

        if not semester:
            raise serializers.ValidationError(
                {"admission_semester": "No semester exists in the database yet. Please seed or create a Semester first."}
            )
        
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['university_id'],
                email=validated_data['email'],
                password=validated_data['password'],
                first_name=validated_data['full_name']
            )

            Student.objects.create(
                user=user,
                university_id=validated_data['university_id'],
                full_name=validated_data['full_name'],
                full_name_ar=validated_data.get('full_name_ar', ''),
                academic_level=validated_data.get('academic_level', 1),
                admission_semester=semester,
            )
        return user