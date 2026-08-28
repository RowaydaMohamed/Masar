from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import CourseSerializer


def ping(request):
    return JsonResponse({"status": "ok"})


FAKE_COURSES = [
    {"id": 1, "code": "CS111", "name": "Introduction to Computers", "credits": 3},
    {"id": 2, "code": "CS112", "name": "Programming I", "credits": 3},
]


@api_view(['GET'])
def courses(request):
    serializer = CourseSerializer(FAKE_COURSES, many=True)
    return Response(serializer.data)