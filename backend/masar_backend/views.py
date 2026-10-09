from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from academics.models import Course


def ping(request):
    return JsonResponse({"status": "ok"})


@api_view(['GET'])
def courses(request):
    data = [
        {
            "id": c.id,
            "code": c.code,
            "name": c.name_en,
            "credits": c.credit_hours,
        }
        for c in Course.objects.all().order_by("code")
    ]
    return Response(data)