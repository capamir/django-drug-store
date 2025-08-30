# users/urls.py
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('auth/', views.AuthView.as_view(), name='auth'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # AJAX endpoints
    path('api/resend-otp/', views.ResendOTPView.as_view(), name='resend_otp'),
]
