from django.urls import path
from .auth_views import CustomTokenObtainPairView, UserProfileView

urlpatterns = [
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/me/', UserProfileView.as_view(), name='me'),
]
