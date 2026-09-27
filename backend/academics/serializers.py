from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from .models import Student

class CustomToken(TokenObtainPairSerializer):
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