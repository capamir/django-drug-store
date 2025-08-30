# users/forms.py
from django import forms
from django.core.validators import RegexValidator

class PhoneNumberForm(forms.Form):
    phone_number = forms.CharField(
        max_length=11,
        validators=[
            RegexValidator(
                regex=r'^09\d{9}$',
                message='Enter a valid Iranian phone number (09XXXXXXXXX)'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '09123456789',
            'dir': 'ltr'
        })
    )

class OTPVerificationForm(forms.Form):
    phone_number = forms.CharField(widget=forms.HiddenInput())
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        validators=[
            RegexValidator(
                regex=r'^\d{6}$',
                message='OTP must be 6 digits'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center',
            'placeholder': '123456',
            'maxlength': '6',
            'dir': 'ltr'
        })
    )
