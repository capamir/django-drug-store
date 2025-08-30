# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTPVerification

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('phone_number', 'first_name', 'last_name', 'is_phone_verified', 'is_active', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_phone_verified', 'date_joined')
    search_fields = ('phone_number', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('phone_number', 'first_name', 'last_name', 'email')}),
        ('Address', {'fields': ('address', 'city', 'postal_code')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_phone_verified')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'first_name', 'last_name', 'is_active'),
        }),
    )

@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'otp_code', 'is_verified', 'is_used', 'attempts', 'expires_at', 'created_at')
    list_filter = ('is_verified', 'is_used', 'created_at')
    search_fields = ('phone_number',)
    readonly_fields = ('created_at', 'expires_at')
    ordering = ('-created_at',)
