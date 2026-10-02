from django.urls import path
from .auth_views import CustomTokenObtainPairView, UserProfileView, RegisterStudentView
from .ai_views import PredictSpecializationView
from . import dashboard_views
from masar_backend import views as core_views

urlpatterns = [
# Ammar's
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/me/', UserProfileView.as_view(), name='me'),
    path('auth/register/', RegisterStudentView.as_view(), name='register'),
    path('predict/', PredictSpecializationView.as_view(), name='predict_specialization'),
# Mahmoud's
    path('ping/', core_views.ping, name='ping'),
    path('courses/', core_views.courses, name='courses'),
    path('dashboard/', dashboard_views.dashboard, name='dashboard'),
]