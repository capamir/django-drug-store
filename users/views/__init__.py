# Import all views to keep URLs clean
from .auth import PhoneEntryView, OTPVerificationView, ResendOTPView, UserRegistrationView
from .dashboard import UserDashboardView

__all__ = [
    'PhoneEntryView',
    'OTPVerificationView', 
    'ResendOTPView',
    'UserRegistrationView',
    'UserDashboardView',
]
