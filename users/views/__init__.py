# Import all views to keep URLs clean
from .auth import PhoneEntryView, OTPVerificationView, ResendOTPView, UserRegistrationView, UserLogoutView
from .dashboard import UserDashboardView

__all__ = [
    # auth
    'PhoneEntryView',
    'OTPVerificationView', 
    'ResendOTPView',
    'UserRegistrationView',
    'UserLogoutView',
    # dashboard
    'UserDashboardView',
]
