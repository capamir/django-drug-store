from django.contrib.auth.models import BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('Phone number is required')
        
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(phone_number, password, **extra_fields)

class AddressManager(models.Manager):
    def active(self):
        """Get active addresses only"""
        return self.filter(is_active=True)
    
    def by_user(self, user):
        """Get addresses for specific user"""
        return self.filter(user=user, is_active=True)
    
    def get_user_default_address(self, user):
        """Get user's default address - this is a query operation"""
        return self.filter(
            user=user, 
            is_default=True, 
            is_active=True
        ).first()
    
    def in_city(self, city):
        return self.filter(city__icontains=city, is_active=True)
    
    def create_default_address(self, user, **kwargs):
        """Create address and set as default"""
        # Set all other addresses as non-default
        self.filter(user=user, is_default=True).update(is_default=False)
        kwargs['is_default'] = True
        return self.create(user=user, **kwargs)

