# accounts/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('auth/register/', views.register_view, name='register'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/verify-2fa/', views.verify_2fa_view, name='verify_2fa'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('user/me/', views.user_me, name='user_me'),
]
