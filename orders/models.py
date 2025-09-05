# orders/models.py
from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.utils import timezone

User = get_user_model()

class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'در انتظار تأیید'),
        ('confirmed', 'تأیید شده'),
        ('preparing', 'در حال آماده‌سازی'),
        ('shipped', 'ارسال شده'),
        ('delivered', 'تحویل داده شده'),
        ('cancelled', 'لغو شده'),
        ('returned', 'مرجوعی'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شده'),
        ('failed', 'پرداخت ناموفق'),
        ('refunded', 'بازگشت وجه'),
    ]
    
    # Order Identification
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')
    
    # Order Status
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Financial Information (Iranian Rial)
    subtotal = models.DecimalField(max_digits=12, decimal_places=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=0)
    
    # Shipping Information
    shipping_address = models.JSONField(help_text='آدرس ارسال به صورت JSON')
    estimated_delivery_date = models.DateField(null=True, blank=True)
    
    # Customer Information
    customer_phone = models.CharField(max_length=11)
    customer_name = models.CharField(max_length=100)
    
    # Notes
    customer_notes = models.TextField(blank=True, help_text='یادداشت مشتری')
    admin_notes = models.TextField(blank=True, help_text='یادداشت مدیریت')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        verbose_name = 'سفارش'
        verbose_name_plural = 'سفارشات'
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        
        # Auto-populate customer info from user profile
        if not self.customer_name:
            self.customer_name = self.user.get_full_name()
        if not self.customer_phone:
            self.customer_phone = self.user.phone_number
            
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Generate unique order number"""
        import random
        import string
        from datetime import datetime
        
        # Format: ORD-YYMMDD-XXXX (ORD-240101-1234)
        date_part = datetime.now().strftime('%y%m%d')
        random_part = ''.join(random.choices(string.digits, k=4))
        return f"ORD-{date_part}-{random_part}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    
    # Product snapshot at time of order
    product_name = models.CharField(max_length=100)
    product_sku = models.CharField(max_length=50)
    unit_price = models.DecimalField(max_digits=12, decimal_places=0)
    
    # Order specifics
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=0)
    
    # Discounts applied to this item
    discount_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_items'
        unique_together = ['order', 'product']
        verbose_name = 'آیتم سفارش'
        verbose_name_plural = 'آیتم‌های سفارش'
    
    def save(self, *args, **kwargs):
        # Calculate line total
        self.line_total = (self.unit_price * self.quantity) - self.discount_amount
        
        # Store product snapshot
        if not self.product_name:
            self.product_name = self.product.name
            self.product_sku = self.product.sku
            
        super().save(*args, **kwargs)

    def for_authenticated_user(self, user):
        """Get all orders for authenticated user with user verification"""
        if not user.is_authenticated:
            return self.none()
        return self.filter(user=user)
    
    def user_order_history(self, user, limit=10):
        """Get recent order history for user"""
        return self.for_authenticated_user(user).order_by('-created_at')[:limit]
    
    def user_total_spent(self, user):
        """Calculate total amount spent by user"""
        return self.filter(
            user=user, 
            payment_status='paid'
        ).aggregate(
            total=models.Sum('total_amount')
        )['total'] or 0

class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_status_history'
        ordering = ['-created_at']
        verbose_name = 'تاریخچه وضعیت سفارش'
        verbose_name_plural = 'تاریخچه وضعیت سفارشات'
