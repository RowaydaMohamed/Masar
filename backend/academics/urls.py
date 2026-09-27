from django.urls import path
from .auth_views import CustomTokenObtainPairView

urlpatterns = [
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
]
