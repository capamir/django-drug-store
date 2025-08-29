from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import random
import string
from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=11, unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.phone_number
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.phone_number
    
    def get_short_name(self):
        return self.first_name or self.phone_number

class OTPVerification(models.Model):
    phone_number = models.CharField(max_length=11)
    otp_code = models.CharField(max_length=6)
    attempts = models.IntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'otp_verifications'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OTP for {self.phone_number} - {self.otp_code}"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @classmethod
    def generate_otp(cls, phone_number):
        """Generate a new OTP for the given phone number"""
        from django.conf import settings
        
        # Invalidate previous OTPs
        cls.objects.filter(
            phone_number=phone_number,
            is_used=False
        ).update(is_used=True)
        
        # Generate new OTP
        otp_code = ''.join(random.choices(string.digits, k=6))
        expires_at = timezone.now() + timezone.timedelta(
            minutes=getattr(settings, 'OTP_EXPIRE_MINUTES', 5)
        )
        
        otp = cls.objects.create(
            phone_number=phone_number,
            otp_code=otp_code,
            expires_at=expires_at
        )
        
        return otp
    
    def verify_otp(self, entered_otp):
        """Verify the entered OTP"""
        from django.conf import settings
        
        max_attempts = getattr(settings, 'OTP_MAX_ATTEMPTS', 3)
        
        if self.is_used or self.is_expired:
            return False, "OTP has expired or already been used"
        
        if self.attempts >= max_attempts:
            return False, "Maximum attempts exceeded"
        
        self.attempts += 1
        self.save()
        
        if self.otp_code == entered_otp:
            self.is_verified = True
            self.is_used = True
            self.save()
            return True, "OTP verified successfully"
        
        return False, f"Invalid OTP. {max_attempts - self.attempts} attempts remaining"
