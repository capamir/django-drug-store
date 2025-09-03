from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from datetime import timedelta
import random
import string
from .managers import UserManager, AddressManager
from .validators import IranianPostalCodeValidator, IranianPhoneValidator, IranianNationalIdValidator

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
    
    national_id = models.CharField(
        max_length=10, 
        validators=[IranianNationalIdValidator],
        blank=True, 
        help_text='کد ملی',
    )
    birth_date = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=1,
        choices=[('M', 'مرد'), ('F', 'زن')],
        blank=True
    )
    
    # Marketing preferences
    sms_notifications = models.BooleanField(
        default=True,
        help_text='دریافت اطلاعیه‌ها از طریق پیامک'
    )
    
    # Customer status
    is_vip = models.BooleanField(default=False)
    total_orders = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(
        max_digits=12, 
        decimal_places=0, 
        default=0
    )

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
    
    def get_default_address(self):
        """Get user's default address"""
        return self.addresses.filter(is_default=True, is_active=True).first()
    
    def get_active_addresses(self):
        """Get all active addresses for user"""
        return self.addresses.filter(is_active=True)
    
    def set_password(self, raw_password):
        """Allow passwords only for staff users"""
        if self.is_staff or self.is_superuser:
            super().set_password(raw_password)
        else:
            # Regular users don't use passwords
            pass
    
    def check_password(self, raw_password):
        """Check password only for staff users"""
        if self.is_staff or self.is_superuser:
            return super().check_password(raw_password)
        else:
            # Regular users authenticate via OTP only
            return False
    
    def has_usable_password(self):
        """Only staff users have usable passwords"""
        return self.is_staff or self.is_superuser

    @property
    def has_complete_profile(self):
        """Check if user has completed their profile"""
        return all([
            self.first_name,
            self.last_name,
            self.email,
            self.is_phone_verified,
            self.get_default_address()
        ])

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
    def can_generate_otp(cls, phone_number):
        """Check if OTP can be generated (rate limiting)"""
        from django.conf import settings
        
        rate_limit_minutes = getattr(settings, 'OTP_RATE_LIMIT_MINUTES', 2)
        cutoff_time = timezone.now() - timedelta(minutes=rate_limit_minutes)
        
        recent_otps = cls.objects.filter(
            phone_number=phone_number,
            created_at__gte=cutoff_time
        ).count()
        
        max_requests = getattr(settings, 'OTP_MAX_REQUESTS_PER_PERIOD', 3)
        return recent_otps < max_requests
    
    @classmethod
    def generate_otp(cls, phone_number):
        """Generate a new OTP for the given phone number"""
        otp, _ = cls.generate_otp_with_user_status(phone_number)
        return otp
    
    @classmethod
    def get_latest_otp(cls, phone_number):
        """Get the latest unused OTP for phone number"""
        return cls.objects.filter(
            phone_number=phone_number,
            is_used=False
        ).first()
    
    def verify_otp(self, entered_otp):
        """Verify the entered OTP"""
        from django.conf import settings
        
        max_attempts = getattr(settings, 'OTP_MAX_ATTEMPTS', 3)
        
        if self.is_used or self.is_expired:
            return False, "کد تأیید منقضی شده یا قبلاً استفاده شده"
        
        if self.attempts >= max_attempts:
            return False, "تعداد تلاش‌های مجاز تمام شده"
        
        self.attempts += 1
        self.save()
        
        if self.otp_code == entered_otp:
            self.is_verified = True
            self.is_used = True
            self.save()
            return True, "کد تأیید با موفقیت تأیید شد"
        
        remaining = max_attempts - self.attempts
        return False, f"کد تأیید اشتباه. {remaining} تلاش باقی مانده"
    
    def get_time_remaining(self):
        """Get remaining time in seconds until expiration"""
        if self.is_expired:
            return 0
        
        remaining = self.expires_at - timezone.now()
        return max(0, int(remaining.total_seconds()))
    
    @classmethod
    def generate_otp_with_user_status(cls, phone_number):
        """Generate OTP and return user existence status"""
        from django.conf import settings
        
        # Check if user exists
        user_exists = User.objects.filter(phone_number=phone_number).exists()
        
        # Check rate limiting
        if not cls.can_generate_otp(phone_number):
            raise ValueError("لطفاً ۲ دقیقه صبر کنید و مجدداً تلاش کنید")
        
        # Invalidate previous unused OTPs
        cls.objects.filter(
            phone_number=phone_number,
            is_used=False
        ).update(is_used=True)
        
        # Generate new OTP
        otp_code = ''.join(random.choices(string.digits, k=6))
        expires_at = timezone.now() + timedelta(
            minutes=getattr(settings, 'OTP_EXPIRE_MINUTES', 5)
        )
        
        otp = cls.objects.create(
            phone_number=phone_number,
            otp_code=otp_code,
            expires_at=expires_at
        )
        
        return otp, user_exists

class Address(models.Model):
    ADDRESS_TYPES = [
        ('home', 'خانه'),
        ('work', 'محل کار'),
        ('other', 'سایر'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='addresses'
    )
    title = models.CharField(
        max_length=50, 
        help_text='نام آدرس (مثل: خانه، محل کار)'
    )
    address_type = models.CharField(
        max_length=10, 
        choices=ADDRESS_TYPES, 
        default='home'
    )
    
    # Geographic Information
    province = models.CharField(max_length=50, help_text='استان')
    city = models.CharField(max_length=50, help_text='شهر') 
    district = models.CharField(max_length=50, blank=True, help_text='منطقه/محله')
    street = models.CharField(max_length=200, help_text='خیابان و کوچه')
    alley = models.CharField(max_length=100, blank=True, help_text='کوچه/پلاک')
    building_number = models.CharField(max_length=20, blank=True, help_text='شماره ساختمان')
    unit = models.CharField(max_length=10, blank=True, help_text='واحد')
    postal_code = models.CharField(max_length=10, help_text='کد پستی', validators=[IranianPostalCodeValidator])
    
    # Contact Information
    recipient_name = models.CharField(
        max_length=100, 
        help_text='نام گیرنده'
    )
    recipient_phone = models.CharField(
        max_length=11, 
        help_text='شماره تماس گیرنده',
        validators=[IranianPhoneValidator]
    )
    
    # Additional Information
    description = models.TextField(
        blank=True, 
        help_text='توضیحات تکمیلی (نشانی دقیق)'
    )
    
    # # Geographic Coordinates (for delivery optimization)
    # latitude = models.DecimalField(
    #     max_digits=10, 
    #     decimal_places=7, 
    #     null=True, 
    #     blank=True
    # )
    # longitude = models.DecimalField(
    #     max_digits=10, 
    #     decimal_places=7, 
    #     null=True, 
    #     blank=True
    # )
    
    # Status and Metadata
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = AddressManager()

    class Meta:
        db_table = 'user_addresses'
        verbose_name = 'آدرس کاربر'
        verbose_name_plural = 'آدرس‌های کاربران'
        ordering = ['-is_default', '-created_at']
        
    def __str__(self):
        return f"{self.title} - {self.user.get_full_name()}"
    
    def get_full_address(self):
        """Return complete formatted address"""
        parts = [
            self.province,
            self.city,
            self.district,
            self.street,
            self.alley,
            self.building_number,
            f"واحد {self.unit}" if self.unit else None,
        ]
        return '، '.join(filter(None, parts))
    
    def save(self, *args, **kwargs):
        # Ensure only one default address per user
        if self.is_default:
            Address.objects.filter(
                user=self.user, 
                is_default=True
            ).update(is_default=False)
        super().save(*args, **kwargs)
