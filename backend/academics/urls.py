from django.urls import path
from .auth_views import RegisterStudentView
from .ai_views import PredictSpecializationView

urlpatterns = [
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/me/', UserProfileView.as_view(), name='me'),
    path('auth/register/', RegisterStudentView.as_view(), name='register'),
    path('predict/', PredictSpecializationView.as_view(), name='predict_specialization'),
]