from django.shortcuts import redirect
from django.views.generic import FormView
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib.auth import login, logout
from django.http import JsonResponse
from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from users.forms import PhoneNumberForm, OTPVerificationForm, UserRegistrationForm
from users.models import User, OTPVerification


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
        
        # CAPTURE NEXT URL FROM REQUEST - IMPORTANT FIX
        next_url = self.request.GET.get('next') or self.request.POST.get('next')

        try:
            # Generate OTP with user status detection
            otp, user_exists = OTPVerification.generate_otp_with_user_status(phone_number)
            
            # Store session data for next steps
            self.request.session['phone_number'] = phone_number
            self.request.session['user_exists'] = user_exists
            self.request.session['otp_generated_at'] = timezone.now().isoformat()
            
            # STORE NEXT URL IN SESSION - IMPORTANT FIX
            if next_url:
                self.request.session['next_url'] = next_url

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


class OTPVerificationView(FormView):
    """
    Step 2: Verify OTP code and handle login/registration flow
    Routes user based on whether they exist or need registration
    """
    template_name = 'users/otp_verification.html'
    form_class = OTPVerificationForm
    
    def dispatch(self, request, *args, **kwargs):
        """Ensure user came from phone entry step"""
        if not request.session.get('phone_number'):
            messages.error(request, 'لطفاً ابتدا شماره موبایل خود را وارد کنید')
            return redirect('users:phone_entry')
        
        if request.user.is_authenticated:
            messages.info(request, 'شما قبلاً وارد شده‌اید')
            return redirect('users:user_dashboard')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form(self, form_class=None):
        """Pre-populate phone number from session"""
        form = super().get_form(form_class)
        form.fields['phone_number'].initial = self.request.session.get('phone_number')
        return form
    
    def form_valid(self, form):
        """Verify OTP and handle user authentication"""
        phone_number = form.cleaned_data['phone_number']
        entered_otp = form.cleaned_data['otp_code']
        print(f"Before setting session: {dict(self.request.session)}")
        self.request.session['otp_verified'] = True
        self.request.session['phone_number'] = phone_number
        print(f"After setting session: {dict(self.request.session)}")
        try:
            # Get the latest OTP for this phone number
            otp_instance = OTPVerification.get_latest_otp(phone_number)
            
            if not otp_instance:
                messages.error(self.request, 'کد تأیید یافت نشد. لطفاً مجدداً درخواست دهید')
                return redirect('users:phone_entry')
            
            # Verify the OTP
            is_valid, message = otp_instance.verify_otp(entered_otp)
            
            if is_valid:
                # OTP verified successfully
                user_exists = self.request.session.get('user_exists', False)
                
                if user_exists:
                    # Login existing user
                    return self._login_existing_user(phone_number)
                else:
                    # Redirect to registration for new users
                    return self._handle_new_user_registration(phone_number)
            
            else:
                # OTP verification failed
                messages.error(self.request, message)
                return self.form_invalid(form)
                
        except Exception as e:
            messages.error(self.request, 'خطا در تأیید کد. لطفاً مجدداً تلاش کنید')
            return self.form_invalid(form)
    
    def _login_existing_user(self, phone_number):
        """Login existing user after OTP verification"""
        try:
            user = User.objects.get(phone_number=phone_number)
            
            # Update phone verification status
            if not user.is_phone_verified:
                user.is_phone_verified = True
                user.save()
            
            # Login user
            login(self.request, user)

            # Get next URL BEFORE clearing session
            next_url = self.request.session.get('next_url')
            
            # Clear session data
            self._clear_auth_session()
            
            # Welcome message
            messages.success(
                self.request, 
                f'خوش آمدید {user.get_full_name()}!'
            )
            
            # IMPROVED REDIRECT LOGIC - IMPORTANT FIX
            if next_url:
                # Don't redirect directly to POST endpoints
                if '/cart/add/' in next_url:
                    # Redirect to cart page instead of direct add action
                    messages.info(self.request, 'لطفاً محصول مورد نظر را مجدداً به سبد خرید اضافه کنید')
                    return redirect('orders:cart')
                else:
                    return redirect(next_url)
            
            return redirect('users:user_dashboard')
            
        except User.DoesNotExist:
            messages.error(self.request, 'کاربر یافت نشد')
            return redirect('users:phone_entry')
    
    def _handle_new_user_registration(self, phone_number):
        """Handle new user registration flow"""
        self.request.session['otp_verified'] = True
        self.request.session['otp_verified_at'] = timezone.now().isoformat()
        self.request.session['user_exists'] = False  # Explicitly set this
        
        messages.success(
            self.request,
            'شماره موبایل تأیید شد. لطفاً اطلاعات خود را تکمیل کنید'
        )
        
        return redirect('users:user_registration')
    
    def _clear_auth_session(self):
        """Clear authentication-related session data"""
        session_keys = [
            'phone_number', 'user_exists', 'otp_generated_at', 
            'otp_verified', 'otp_verified_at'
        ]
        for key in session_keys:
            self.request.session.pop(key, None)
    
    def get_context_data(self, **kwargs):
        """Add context for template"""
        context = super().get_context_data(**kwargs)
        
        phone_number = self.request.session.get('phone_number')
        user_exists = self.request.session.get('user_exists', False)
        
        # Masked phone number for display
        if phone_number and len(phone_number) == 11:
            masked_phone = f"{phone_number[:4]}***{phone_number[-2:]}"
        else:
            masked_phone = phone_number
        
        # Get OTP expiration info
        otp_instance = OTPVerification.get_latest_otp(phone_number)
        time_remaining = 0
        if otp_instance and not otp_instance.is_expired:
            time_remaining = otp_instance.get_time_remaining()
        
        context.update({
            'page_title': 'تأیید شماره موبایل',
            'page_description': f'کد تأیید ارسال شده به {masked_phone} را وارد کنید',
            'phone_number': phone_number,
            'masked_phone': masked_phone,
            'user_exists': user_exists,
            'time_remaining': time_remaining,
            'flow_type': 'ورود' if user_exists else 'ثبت نام',
        })
        
        return context


class ResendOTPView(FormView):
    """
    AJAX view to resend OTP code
    Can be called from OTP verification page
    """
    form_class = PhoneNumberForm
    
    def post(self, request, *args, **kwargs):
        """Handle AJAX resend OTP request"""
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            messages.error(request, 'درخواست نامعتبر')
            return redirect('users:otp_verification')
        
        phone_number = request.session.get('phone_number')
        if not phone_number:
            return JsonResponse({
                'success': False, 
                'message': 'شماره موبایل یافت نشد'
            })
        
        try:
            # Generate new OTP using simple method
            otp = OTPVerification.generate_otp(phone_number)
            
            # Send SMS
            self._send_otp_sms(phone_number, otp.otp_code)
            
            # Update session
            request.session['otp_generated_at'] = timezone.now().isoformat()
            
            return JsonResponse({
                'success': True,
                'message': 'کد تأیید مجدداً ارسال شد',
                'time_remaining': otp.get_time_remaining()
            })
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
        except Exception:
            return JsonResponse({
                'success': False,
                'message': 'خطا در ارسال مجدد کد تأیید'
            })
    
    def _send_otp_sms(self, phone_number, otp_code):
        """Send OTP via SMS - same as PhoneEntryView"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'Resend OTP for {phone_number}: {otp_code}')
        return True


class UserRegistrationView(FormView):
    """
    Step 3: Complete user registration after OTP verification
    Only for new users who have successfully verified their phone number
    """
    template_name = 'users/user_registration.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('users:user_dashboard')
    
    def dispatch(self, request, *args, **kwargs):
        """Validate registration session and redirect if needed"""
        print(f"Registration view session: {dict(self.request.session)}")

        # Check if user is already authenticated
        if request.user.is_authenticated:
            messages.info(request, 'شما قبلاً وارد شده‌اید')
            return redirect('users:user_dashboard')
        
        # Validate session data
        if not self._is_valid_registration_session():
            messages.error(request, 'جلسه منقضی شده. لطفاً مجدداً تلاش کنید')
            return redirect('users:phone_entry')
        
        return super().dispatch(request, *args, **kwargs)
    
    def _is_valid_registration_session(self):
        """Check if registration session is valid"""
        session = self.request.session
        
        # Debug: Print session data
        print(f"Session data: {dict(session)}")
        
        # Required session data
        if not session.get('phone_number'):
            return False
        if not session.get('otp_verified'):
            return False
        
        # Must be for new user registration - IMPORTANT FIX
        if session.get('user_exists') is not False:  # Changed this line
            print("Session indicates existing user, not new registration")
            return False
        
        # Check session hasn't expired
        otp_verified_at = session.get('otp_verified_at')
        if otp_verified_at:
            try:
                verified_time = timezone.datetime.fromisoformat(otp_verified_at)
                if timezone.now() - verified_time > timedelta(minutes=10):
                    return False
            except (ValueError, TypeError):
                return False
        
        return True

    def get_form(self, form_class=None):
        """Pre-populate form with session data"""
        form = super().get_form(form_class)
        phone_number = self.request.session.get('phone_number')
        
        # Use manager method to get registration data
        registration_data = User.objects.get_registration_data(phone_number)
        form.fields['phone_number'].initial = registration_data['phone_number']
        
        return form
    
    def form_valid(self, form):
        """Create user account and login"""
        phone_number = self.request.session.get('phone_number')
        
        try:
            # Use manager method for clean user creation
            user = User.objects.complete_registration(
                phone_number=phone_number,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email']
            )
            
            # Login the new user
            login(self.request, user)
            
            # Clear registration session data
            self._clear_registration_session()
            
            # Welcome message
            messages.success(
                self.request,
                f'خوش آمدید {user.get_full_name()}! حساب شما با موفقیت ایجاد شد'
            )
            
            return super().form_valid(form)
            
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
        except Exception as e:
            messages.error(
                self.request,
                'خطا در ایجاد حساب کاربری. لطفاً مجدداً تلاش کنید'
            )
            return self.form_invalid(form)
    
    def _clear_registration_session(self):
        """Clear registration-related session data"""
        session_keys = [
            'phone_number', 'user_exists', 'otp_generated_at',
            'otp_verified', 'otp_verified_at'
        ]
        for key in session_keys:
            self.request.session.pop(key, None)
    
    def get_context_data(self, **kwargs):
        """Add context for template"""
        context = super().get_context_data(**kwargs)
        
        phone_number = self.request.session.get('phone_number')
        masked_phone = f"{phone_number[:4]}***{phone_number[-2:]}" if phone_number else ''
        
        context.update({
            'page_title': 'تکمیل ثبت نام',
            'page_description': 'برای تکمیل ثبت نام، اطلاعات زیر را وارد کنید',
            'phone_number': phone_number,
            'masked_phone': masked_phone,
            'step_number': 3,
            'total_steps': 3,
        })
        
        return context


class UserLogoutView(LoginRequiredMixin, View):
    def get(self, request):
        logout(request)
        messages.success(request, 'شما با موفقیت خارج شدید', 'success')
        return redirect('products:home')  # Changed from 'home:home' to 'products:home'
