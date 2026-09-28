from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from .models import Student
from rest_framework import serializers


# For auth_views.py

# Replacing the email or the "identifier" with the students user name
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['identifier'] = self.fields.pop('username')
    
    def validate(self, attrs):
        identifier = attrs.get('identifier')
        if "@" in identifier:# if a user used an email to sign in
            try:
                student = Student.objects.get(university_email=identifier)
                attrs['username'] = student.user.username
            except Student.DoesNotExist:
                    raise AuthenticationFailed("Invalid email or password.")
        else:
            attrs['username'] = identifier
        del attrs['identifier']

        return super().validate(attrs)


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['university_email', 'full_name', 'entry_year',
                'academic_level', 'department', 'cgpa', 'status']