# users/urls.py
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # # Authentication URLs
    path('login/', views.PhoneEntryView.as_view(), name='phone_entry'),
    path('verify/', views.OTPVerificationView.as_view(), name='otp_verification'),  
    path('register/', views.UserRegistrationView.as_view(), name='user_registration'),

    # AJAX endpoint for OTP resend
    path('resend-otp/', views.ResendOTPView.as_view(), name='resend_otp'),

    # Dashboard URLs
    path('dashboard/', views.UserDashboardView.as_view(), name='user_dashboard'),
]
