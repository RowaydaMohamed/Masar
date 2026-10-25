from django.urls import path
from .auth_views import CustomTokenObtainPairView, UserProfileView, RegisterStudentView
from .ai_views import PredictSpecializationView
from . import dashboard_views, tree_views
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
    
    # Dashboard API
    path('dashboard/', dashboard_views.dashboard, name='dashboard'),
    
    # Trees & Academics APIs
    path('curriculum-tree/', tree_views.curriculum_tree, name='curriculum-tree'),
    path('requirements/', tree_views.requirements_progress, name='requirements'),
    path('graduation-path/', tree_views.graduation_path, name='graduation-path'),
    path('me/history/', tree_views.student_history, name='student-history'),
]