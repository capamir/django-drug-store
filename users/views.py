# users/views.py
from django.views.generic import FormView, TemplateView
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .forms import PhoneNumberForm, OTPVerificationForm
from .services import OTPAuthService

class AuthView(FormView):
    """Unified authentication view for login/register via OTP"""
    template_name = 'users/auth.html'
    form_class = PhoneNumberForm
    success_url = reverse_lazy('users:dashboard')
    
    def dispatch(self, request, *args, **kwargs):
        """Redirect authenticated users to dashboard"""
        if request.user.is_authenticated:
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Add OTP form and show_otp_form flag to context"""
        context = super().get_context_data(**kwargs)
        show_otp_form = self.request.session.get('show_otp_form', False)
        phone_number = self.request.session.get('auth_phone_number', '')
        
        context.update({
            'otp_form': OTPVerificationForm(initial={'phone_number': phone_number}),
            'show_otp_form': show_otp_form
        })
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle both phone number submission and OTP verification"""
        if 'send_otp' in request.POST:
            return self.handle_phone_submission(request)
        elif 'verify_otp' in request.POST:
            return self.handle_otp_verification(request)
        
        return self.form_invalid(self.get_form())
    
    def handle_phone_submission(self, request):
        """Process phone number and send OTP"""
        form = PhoneNumberForm(request.POST)
        
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']
            success, message = OTPAuthService.send_otp(phone_number)
            
            if success:
                messages.success(request, message)
                request.session['auth_phone_number'] = phone_number
                request.session['show_otp_form'] = True
            else:
                messages.error(request, message)
        
        # Return to form with updated context
        context = self.get_context_data(form=form)
        return self.render_to_response(context)
    
    def handle_otp_verification(self, request):
        """Process OTP verification and login/register user"""
        otp_form = OTPVerificationForm(request.POST)
        
        if otp_form.is_valid():
            phone_number = otp_form.cleaned_data['phone_number']
            otp_code = otp_form.cleaned_data['otp_code']
            
            success, message = OTPAuthService.verify_and_login(
                request, phone_number, otp_code
            )
            
            if success:
                messages.success(request, message)
                # Clean up session
                request.session.pop('auth_phone_number', None)
                request.session.pop('show_otp_form', None)
                return redirect(self.success_url)
            else:
                messages.error(request, message)
        
        # Return to OTP form with errors
        context = self.get_context_data(
            form=PhoneNumberForm(initial={'phone_number': otp_form.data.get('phone_number', '')}),
            otp_form=otp_form
        )
        context['show_otp_form'] = True
        return self.render_to_response(context)

class DashboardView(LoginRequiredMixin, TemplateView):
    """User dashboard - requires authentication"""
    template_name = 'users/dashboard.html'
    login_url = reverse_lazy('users:auth')
    
    def get_context_data(self, **kwargs):
        """Add user-specific dashboard data"""
        context = super().get_context_data(**kwargs)
        context.update({
            'user': self.request.user,
            # Add more dashboard data here later
        })
        return context

class LogoutView(TemplateView):
    """Handle user logout"""
    
    def get(self, request, *args, **kwargs):
        """Logout user and redirect to auth page"""
        if request.user.is_authenticated:
            logout(request)
            messages.info(request, 'شما با موفقیت خارج شدید')
        return redirect('users:auth')

@method_decorator(require_http_methods(["POST"]), name='dispatch')
class ResendOTPView(TemplateView):
    """AJAX endpoint for resending OTP"""
    
    def post(self, request, *args, **kwargs):
        """Resend OTP to stored phone number"""
        phone_number = request.session.get('auth_phone_number')
        
        if not phone_number:
            return JsonResponse({
                'success': False, 
                'message': 'جلسه منقضی شده است. لطفا مجدد تلاش کنید'
            })
        
        success, message = OTPAuthService.send_otp(phone_number)
        
        return JsonResponse({
            'success': success,
            'message': message
        })
