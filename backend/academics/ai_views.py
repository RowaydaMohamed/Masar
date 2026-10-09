from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .ai_utils import predict_specialization

class PredictSpecializationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        grades_list = request.data.get('grades', [])
        
        if len(grades_list) != 24:
            return Response({"error": "Please provide exactly 24 grades."}, status=400)
        
        prediction = predict_specialization(grades_list)
        
        return Response({"predicted_department": prediction})