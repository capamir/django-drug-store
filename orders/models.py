# orders/models.py
from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.utils import timezone

User = get_user_model()


class Cart(models.Model):
    """Shopping cart for authenticated users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'carts'
        verbose_name = 'سبد خرید'
        verbose_name_plural = 'سبدهای خرید'
    
    def __str__(self):
        return f"سبد خرید {self.user.get_full_name() or self.user.phone_number}"
    
    @property
    def total_items(self):
        """Get total number of items in cart"""
        return self.items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
    
    @property
    def subtotal_price(self):
        """Calculate subtotal price of cart"""
        total = Decimal('0')
        for item in self.items.select_related('product'):
            total += item.line_total
        return total
    
    @property
    def is_empty(self):
        """Check if cart is empty"""
        return not self.items.exists()
    
    def clear(self):
        """Clear all items from cart"""
        self.items.all().delete()
        
    def get_total_discount(self):
        """Calculate total discount amount"""
        total_discount = Decimal('0')
        for item in self.items.select_related('product'):
            if item.product.has_discount:
                original_price = item.product.unit_price * item.quantity
                discounted_price = item.line_total
                total_discount += (original_price - discounted_price)
        return total_discount


class CartItem(models.Model):
    """Individual item in shopping cart"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cart_items'
        verbose_name = 'آیتم سبد خرید'
        verbose_name_plural = 'آیتم‌های سبد خرید'
        unique_together = ['cart', 'product']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
    
    @property
    def line_total(self):
        """Calculate line total with discounts applied"""
        if self.product.has_discount:
            return self.product.effective_unit_price * self.quantity
        return self.product.unit_price * self.quantity
    
    @property
    def unit_price(self):
        """Get effective unit price"""
        return self.product.effective_unit_price
    
    @property
    def original_line_total(self):
        """Get original line total without discounts"""
        return self.product.unit_price * self.quantity
    
    @property
    def discount_amount(self):
        """Get discount amount for this item"""
        if self.product.has_discount:
            return self.original_line_total - self.line_total
        return Decimal('0')
    
    def save(self, *args, **kwargs):
        # Validate quantity against stock
        if self.quantity > self.product.quantity:
            raise ValueError(f'موجودی {self.product.name} کافی نیست.')
        super().save(*args, **kwargs)


class Order(models.Model):
    """Customer order"""
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
    
    # Link to original cart (optional, for reference)
    cart = models.OneToOneField(Cart, on_delete=models.SET_NULL, null=True, blank=True, related_name='order')
    
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
    
    objects = models.Manager()  # We'll add custom manager in managers.py
    
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
        
        # Ensure uniqueness
        while True:
            date_part = datetime.now().strftime('%y%m%d')
            random_part = ''.join(random.choices(string.digits, k=4))
            order_number = f"ORD-{date_part}-{random_part}"
            
            if not Order.objects.filter(order_number=order_number).exists():
                return order_number
    
    def __str__(self):
        return f"سفارش {self.order_number}"
    
    @property
    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        return self.status in ['pending', 'confirmed'] and self.payment_status != 'paid'
    
    @property
    def can_be_returned(self):
        """Check if order can be returned"""
        return (
            self.status == 'delivered' and
            self.payment_status == 'paid' and
            self.delivered_at and
            (timezone.now().date() - self.delivered_at.date()).days <= 7
        )
    
    @property
    def items_count(self):
        """Get total number of items in order"""
        return self.items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0


class OrderItem(models.Model):
    """Individual item in an order"""
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
        ordering = ['id']
    
    def save(self, *args, **kwargs):
        # Calculate line total
        self.line_total = (self.unit_price * self.quantity) - self.discount_amount
        
        # Store product snapshot
        if not self.product_name:
            self.product_name = self.product.name
            self.product_sku = self.product.sku
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.quantity}x {self.product_name} - {self.order.order_number}"


class OrderStatusHistory(models.Model):
    """History of order status changes"""
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
    
    def __str__(self):
        return f"{self.order.order_number}: {self.previous_status} → {self.new_status}"
