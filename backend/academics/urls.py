from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .auth_views import CustomTokenObtainPairView, UserProfileView, RegisterStudentView
from .ai_views import PredictSpecializationView
from . import dashboard_views, tree_views
from masar_backend import views as core_views
from .specialization_views import SpecializationListView

urlpatterns = [
    # Core & Dashboard endpoints
    path('ping/', core_views.ping, name='ping'),
    path('courses/', core_views.courses, name='courses'),
    
    # Dashboard API
    path('dashboard/', dashboard_views.dashboard, name='dashboard'),

    # Auth endpoints
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', UserProfileView.as_view(), name='me'),
    path('auth/register/', RegisterStudentView.as_view(), name='register'),

    # AI endpoint
    path('predict/', PredictSpecializationView.as_view(), name='predict_specialization'),

    # Trees & Academics APIs
    path('curriculum-tree/', tree_views.curriculum_tree, name='curriculum-tree'),
    path('requirements/', tree_views.requirements_progress, name='requirements'),
    path('graduation-path/', tree_views.graduation_path, name='graduation-path'),
    path('me/history/', tree_views.student_history, name='student-history'),

    # Specializations & Trees
    path('specializations/', SpecializationListView.as_view(), name='specializations_list'),
]