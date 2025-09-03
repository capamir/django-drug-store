# users/forms.py
from django import forms
from django.core.validators import RegexValidator
from .models import User, Address
from .validators import IranianPostalCodeValidator, IranianPhoneValidator, IranianNationalIdValidator


class PhoneNumberForm(forms.Form):
    phone_number = forms.CharField(
        max_length=11,
        validators=[IranianPhoneValidator()],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '09123456789',
            'dir': 'ltr'
        }),
        label='شماره موبایل'
    )


class OTPVerificationForm(forms.Form):
    phone_number = forms.CharField(widget=forms.HiddenInput())
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        validators=[
            RegexValidator(
                regex=r'^\d{6}$',
                message='کد تأیید باید ۶ رقم باشد'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center',
            'placeholder': '123456',
            'maxlength': '6',
            'dir': 'ltr',
            'autocomplete': 'one-time-code'
        }),
        label='کد تأیید'
    )


class UserRegistrationForm(forms.ModelForm):
    """For new users after OTP verification - NO PASSWORD"""
    class Meta:
        model = User
        fields = ['phone_number', 'first_name', 'last_name', 'email']
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True  # Phone already verified
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام خانوادگی'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@email.com',
                'dir': 'ltr'
            }),
        }
        labels = {
            'phone_number': 'شماره موبایل',
            'first_name': 'نام',
            'last_name': 'نام خانوادگی',
            'email': 'ایمیل (اختیاری)',
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_phone_verified = True
        if commit:
            user.save()
        return user

class UserProfileForm(forms.ModelForm):
    """Profile editing - NO PASSWORD FIELDS"""
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'national_id', 
            'birth_date', 'gender', 'sms_notifications'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام خانوادگی'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@email.com',
                'dir': 'ltr'
            }),
            'national_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1234567890',
                'dir': 'ltr',
                'maxlength': '10'
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-select'
            }),
            'sms_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'first_name': 'نام',
            'last_name': 'نام خانوادگی', 
            'email': 'ایمیل',
            'national_id': 'کد ملی',
            'birth_date': 'تاریخ تولد',
            'gender': 'جنسیت',
            'sms_notifications': 'دریافت پیامک اطلاع‌رسانی',
        }

    def clean_national_id(self):
        national_id = self.cleaned_data['national_id']
        if national_id:
            validator = IranianNationalIdValidator()
            validator(national_id)
        return national_id


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            'title', 'address_type', 'province', 'city', 'district',
            'street', 'alley', 'building_number', 'unit', 'postal_code',
            'recipient_name', 'recipient_phone', 'description', 'is_default'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مثال: خانه، محل کار'
            }),
            'address_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'province': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'تهران'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'تهران'
            }),
            'district': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'منطقه ۱'
            }),
            'street': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'خیابان ولیعصر'
            }),
            'alley': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'کوچه شهید احمدی'
            }),
            'building_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '۱۲۳'
            }),
            'unit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '۵'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1234567890',
                'dir': 'ltr',
                'maxlength': '10'
            }),
            'recipient_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام و نام خانوادگی گیرنده'
            }),
            'recipient_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '09123456789',
                'dir': 'ltr'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'توضیحات تکمیلی برای پیدا کردن آدرس'
            }),
            'is_default': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'title': 'عنوان آدرس',
            'address_type': 'نوع آدرس',
            'province': 'استان',
            'city': 'شهر',
            'district': 'منطقه/محله',
            'street': 'خیابان',
            'alley': 'کوچه',
            'building_number': 'پلاک',
            'unit': 'واحد',
            'postal_code': 'کد پستی',
            'recipient_name': 'نام گیرنده',
            'recipient_phone': 'شماره تماس گیرنده',
            'description': 'توضیحات تکمیلی',
            'is_default': 'آدرس پیش‌فرض',
        }

    def clean_postal_code(self):
        postal_code = self.cleaned_data['postal_code']
        validator = IranianPostalCodeValidator()
        validator(postal_code)
        return postal_code

    def clean_recipient_phone(self):
        phone = self.cleaned_data['recipient_phone']
        validator = IranianPhoneValidator()
        validator(phone)
        return phone
