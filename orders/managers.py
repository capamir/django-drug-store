# orders/managers.py
from django.db import models
from django.utils import timezone

class OrderManager(models.Manager):
    
    def pending(self):
        """Get pending orders"""
        return self.filter(status='pending')
    
    def confirmed(self):
        """Get confirmed orders"""
        return self.filter(status='confirmed')
    
    def for_user(self, user):
        """Get orders for specific user"""
        return self.filter(user=user)
    
    def recent(self, days=30):
        """Get recent orders within specified days"""
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=cutoff_date)
    
    def with_items(self):
        """Optimize queries by prefetching order items"""
        return self.prefetch_related('items', 'items__product')
    
    def calculate_daily_sales(self, date=None):
        """Calculate total sales for a specific date"""
        if not date:
            date = timezone.now().date()
        
        return self.filter(
            created_at__date=date,
            payment_status='paid'
        ).aggregate(
            total=models.Sum('total_amount')
        )['total'] or 0
