from django.shortcuts import redirect
from django.views.generic import FormView
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from .forms import PhoneNumberForm
from .models import User, OTPVerification


class PhoneEntryView(FormView):
    """
    Unified login/register view - Step 1: Phone entry
    Handles both existing users (login) and new users (registration)
    """
    template_name = 'users/phone_entry.html'
    form_class = PhoneNumberForm
    success_url = reverse_lazy('users:otp_verification')
    
    def dispatch(self, request, *args, **kwargs):
        """Redirect authenticated users to dashboard"""
        if request.user.is_authenticated:
            messages.info(request, 'شما قبلاً وارد شده‌اید')
            return redirect('users:user_dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """Generate OTP and determine login vs register flow"""
        phone_number = form.cleaned_data['phone_number']
        
        try:
            # Generate OTP with user status detection
            otp, user_exists = OTPVerification.generate_otp_with_user_status(phone_number)
            
            # Store session data for next steps
            self.request.session['phone_number'] = phone_number
            self.request.session['user_exists'] = user_exists
            self.request.session['otp_generated_at'] = timezone.now().isoformat()
            
            # Send OTP via SMS
            self._send_otp_sms(phone_number, otp.otp_code)
            
            # User-specific success messages
            if user_exists:
                messages.success(
                    self.request,
                    f'کد تأیید برای ورود به حساب شما به {phone_number} ارسال شد'
                )
            else:
                messages.success(
                    self.request,
                    f'کد تأیید برای ساخت حساب جدید به {phone_number} ارسال شد'
                )
            
            return super().form_valid(form)
            
        except ValueError as e:
            # Rate limiting or validation errors from model
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        except Exception as e:
            # Unexpected errors (SMS service, etc.)
            messages.error(
                self.request,
                'خطا در ارسال کد تأیید. لطفاً مجدداً تلاش کنید'
            )
            return self.form_invalid(form)
    
    def _send_otp_sms(self, phone_number, otp_code):
        """
        Send OTP via SMS service
        TODO: Implement your SMS provider (Kavenegar, etc.)
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'OTP for {phone_number}: {otp_code}')
        
        # For development - remove in production
        print(f'[DEV] OTP Code: {otp_code}')
        
        return True
    
    def get_context_data(self, **kwargs):
        """Add context for template"""
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'ورود / ثبت نام',
            'page_description': 'برای ورود یا ثبت نام، شماره موبایل خود را وارد کنید',
            'is_unified_auth': True,
        })
        return context
