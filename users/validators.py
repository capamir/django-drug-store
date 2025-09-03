# users/validators.py
from django.core.exceptions import ValidationError
from .utils import (
    validate_iranian_postal_code, 
    validate_iranian_phone, 
    validate_iranian_national_id
)

class IranianPostalCodeValidator:
    def __call__(self, value):
        is_valid, message = validate_iranian_postal_code(value)
        if not is_valid:
            raise ValidationError(message)

class IranianPhoneValidator:
    def __call__(self, value):
        is_valid, message = validate_iranian_phone(value)
        if not is_valid:
            raise ValidationError(message)

class IranianNationalIdValidator:
    def __call__(self, value):
        if not value:  # Allow blank
            return
        is_valid, message = validate_iranian_national_id(value)
        if not is_valid:
            raise ValidationError(message)
