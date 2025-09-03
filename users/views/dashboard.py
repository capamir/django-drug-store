from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib import messages
from django.shortcuts import redirect


class UserDashboardView(LoginRequiredMixin, TemplateView):
    """
    User dashboard home page showing overview of user account
    Shows user details, quick stats, and navigation to other sections
    """
    template_name = 'users/dashboard.html'
    login_url = 'users:phone_entry'
    
    def get_context_data(self, **kwargs):
        """Add dashboard context data"""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # User overview data
        context.update({
            'user': user,
            'user_details': self._get_user_details(user),
            'quick_stats': self._get_quick_stats(user),
            'recent_activity': self._get_recent_activity(user),
            'dashboard_cards': self._get_dashboard_cards(user),
        })
        
        return context
    
    def _get_user_details(self, user):
        """Get user personal details for display"""
        return {
            'full_name': user.get_full_name(),
            'phone_number': user.phone_number,
            'email': user.email or 'وارد نشده',
            'member_since': user.date_joined,
            'is_phone_verified': user.is_phone_verified,
            'is_vip': user.is_vip,
        }
    
    def _get_quick_stats(self, user):
        """Get dashboard statistics"""
        # You can enhance this with actual related models later
        return {
            'total_orders': user.total_orders,
            'total_spent': user.total_spent,
            'saved_addresses': 0,  # Will connect to Address model later
            'wishlist_items': 0,   # Will connect to Wishlist model later
        }
    
    def _get_recent_activity(self, user):
        """Get user's recent activity (placeholder for now)"""
        # This will be populated when you add Order, Address models
        return [
            {
                'type': 'info',
                'message': 'حساب کاربری شما با موفقیت ایجاد شد',
                'date': user.date_joined,
                'icon': 'fas fa-user-check'
            }
        ]
    
    def _get_dashboard_cards(self, user):
        """Get dashboard action cards"""
        return [
            {
                'title': 'سفارشات من',
                'description': f'{user.total_orders} سفارش',
                'icon': 'fas fa-shopping-bag',
                'color': 'primary',
                'url': '#',  # Will add order URLs later
            },
            {
                'title': 'آدرس‌های من',
                'description': 'مدیریت آدرس‌های تحویل',
                'icon': 'fas fa-map-marker-alt',
                'color': 'success',
                'url': '#',  # Will add address URLs later
            },
            {
                'title': 'علاقه‌مندی‌ها',
                'description': 'محصولات مورد علاقه',
                'icon': 'fas fa-heart',
                'color': 'danger',
                'url': '#',
            },
            {
                'title': 'تنظیمات',
                'description': 'ویرایش اطلاعات شخصی',
                'icon': 'fas fa-cog',
                'color': 'info',
                'url': '#',
            }
        ]
