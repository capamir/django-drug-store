# users/services.py
from django.contrib.auth import login
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import OTPVerification
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class OTPAuthService:
    @staticmethod
    def send_otp(phone_number):
        """Generate and send OTP to phone number"""
        try:
            # Clean phone number (remove spaces, etc.)
            clean_phone = phone_number.replace(' ', '').replace('-', '')
            
            if not clean_phone.startswith('09') or len(clean_phone) != 11:
                return False, "Invalid Iranian phone number format"
            
            # Generate OTP
            otp = OTPVerification.generate_otp(clean_phone)
            
            # TODO: Integrate with SMS service (Kavenegar, etc.)
            # For development, we'll just log the OTP
            logger.info(f"OTP for {clean_phone}: {otp.otp_code}")
            print(f"🔐 OTP for {clean_phone}: {otp.otp_code}")  # Remove in production
            
            return True, "OTP sent successfully"
            
        except Exception as e:
            logger.error(f"Error sending OTP to {phone_number}: {str(e)}")
            return False, "Failed to send OTP"
    
    @staticmethod
    def verify_and_login(request, phone_number, otp_code):
        """Verify OTP and login/register user"""
        try:
            clean_phone = phone_number.replace(' ', '').replace('-', '')
            
            # Get the latest OTP for this phone number
            try:
                otp_obj = OTPVerification.objects.filter(
                    phone_number=clean_phone,
                    is_used=False
                ).latest('created_at')
            except OTPVerification.DoesNotExist:
                return False, "No valid OTP found. Please request a new one."
            
            # Verify OTP
            is_valid, message = otp_obj.verify_otp(otp_code)
            
            if not is_valid:
                return False, message
            
            # Get or create user
            user, created = User.objects.get_or_create(
                phone_number=clean_phone,
                defaults={
                    'is_phone_verified': True,
                    'is_active': True
                }
            )
            
            if not created:
                # Update verification status for existing user
                user.is_phone_verified = True
                user.save()
            
            # Login user
            login(request, user)
            
            action = "registered and logged in" if created else "logged in"
            return True, f"Successfully {action}"
            
        except Exception as e:
            logger.error(f"Error during OTP verification: {str(e)}")
            return False, "Authentication failed"
