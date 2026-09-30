"""
URL configuration for masar_backend project.
"""

from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/ping', views.ping),
    path('api/courses', views.courses),
    
    # تحويل أي مسار يبدأ بـ api/ إلى ملف academics.urls
    path('api/', include('academics.urls')),
]