from django.urls import path
from .auth_views import CustomTokenObtainPairView, UserProfileView, RegisterStudentView
from . import dashboard_views
from . import ai_views

urlpatterns = [
    # Auth Endpoints
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/me/', UserProfileView.as_view(), name='me'),
    path('auth/register/', RegisterStudentView.as_view(), name='register'),
    
    # Dashboard Endpoint
    path('dashboard', dashboard_views.dashboard, name='dashboard'),
    
    # AI Recommendation Endpoint (نربطه بـ ai_views بدلاً من dashboard_views)
    path('recommend-specialization', ai_views.recommend_specialization, name='recommend_specialization'),
]