# orders/managers.py
from django.db import models
from django.utils import timezone
from decimal import Decimal


class CartManager(models.Manager):
    """Manager for Cart model"""
    
    def get_or_create_for_user(self, user):
        """Get or create cart for user"""
        cart, created = self.get_or_create(user=user)
        return cart, created
    
    def active_carts(self):
        """Get carts that have items"""
        return self.filter(items__isnull=False).distinct()
    
    def empty_carts(self):
        """Get empty carts"""
        return self.filter(items__isnull=True)
    
    def old_empty_carts(self, days=30):
        """Get old empty carts for cleanup"""
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days)
        return self.filter(
            items__isnull=True,
            updated_at__lt=cutoff_date
        )


class CartItemManager(models.Manager):
    """Manager for CartItem model"""
    
    def for_user(self, user):
        """Get cart items for specific user"""
        return self.filter(cart__user=user)
    
    def with_products(self):
        """Optimize queries by selecting related products"""
        return self.select_related('product', 'product__category')
    
    def available_items(self):
        """Get items where product is still available"""
        return self.filter(
            product__is_active=True,
            product__quantity__gt=0
        )
    
    def unavailable_items(self):
        """Get items where product is no longer available"""
        return self.filter(
            models.Q(product__is_active=False) |
            models.Q(product__quantity=0)
        )


class OrderManager(models.Manager):
    """Enhanced manager for Order model"""
    
    def pending(self):
        """Get pending orders"""
        return self.filter(status='pending')
    
    def confirmed(self):
        """Get confirmed orders"""
        return self.filter(status='confirmed')
    
    def completed(self):
        """Get completed orders (delivered and paid)"""
        return self.filter(status='delivered', payment_status='paid')
    
    def cancelled(self):
        """Get cancelled orders"""
        return self.filter(status='cancelled')
    
    def for_user(self, user):
        """Get orders for specific user"""
        if not user.is_authenticated:
            return self.none()
        return self.filter(user=user)
    
    def recent(self, days=30):
        """Get recent orders within specified days"""
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=cutoff_date)
    
    def with_items(self):
        """Optimize queries by prefetching order items"""
        return self.prefetch_related(
            'items',
            'items__product',
            'items__product__category'
        )
    
    def with_status_history(self):
        """Include status history in queries"""
        return self.prefetch_related('status_history')
    
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
    
    def calculate_monthly_sales(self, year=None, month=None):
        """Calculate total sales for a specific month"""
        if not year:
            year = timezone.now().year
        if not month:
            month = timezone.now().month
        
        return self.filter(
            created_at__year=year,
            created_at__month=month,
            payment_status='paid'
        ).aggregate(
            total=models.Sum('total_amount'),
            count=models.Count('id')
        )
    
    def user_order_history(self, user, limit=10):
        """Get recent order history for user"""
        return self.for_user(user).order_by('-created_at')[:limit]
    
    def user_total_spent(self, user):
        """Calculate total amount spent by user"""
        return self.filter(
            user=user,
            payment_status='paid'
        ).aggregate(
            total=models.Sum('total_amount')
        )['total'] or 0
    
    def needs_processing(self):
        """Get orders that need processing"""
        return self.filter(
            status__in=['pending', 'confirmed'],
            payment_status='paid'
        )
    
    def create_from_cart(self, cart, shipping_address, customer_notes=''):
        """Create order from cart"""
        if cart.is_empty:
            raise ValueError('سبد خرید خالی است.')
        
        # Calculate totals
        subtotal = cart.subtotal_price
        discount_amount = cart.get_total_discount()
        shipping_cost = self._calculate_shipping_cost(subtotal)
        total_amount = subtotal + shipping_cost
        
        # Create order
        order = self.create(
            user=cart.user,
            cart=cart,
            subtotal=subtotal,
            discount_amount=discount_amount,
            shipping_cost=shipping_cost,
            total_amount=total_amount,
            shipping_address=shipping_address,
            customer_notes=customer_notes,
        )
        
        # Create order items from cart items
        from .models import OrderItem
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                product_name=cart_item.product.name,
                product_sku=cart_item.product.sku,
                unit_price=cart_item.product.unit_price,
                quantity=cart_item.quantity,
                discount_amount=cart_item.discount_amount,
            )
            
            # Update product inventory
            product = cart_item.product
            product.quantity -= cart_item.quantity
            product.save()
        
        return order
    
    def _calculate_shipping_cost(self, subtotal):
        """Calculate shipping cost based on subtotal"""
        # Free shipping over 500,000 Rials
        if subtotal >= Decimal('500000'):
            return Decimal('0')
        return Decimal('25000')


class OrderItemManager(models.Manager):
    """Manager for OrderItem model"""
    
    def for_order(self, order):
        """Get items for specific order"""
        return self.filter(order=order)
    
    def for_product(self, product):
        """Get order items for specific product"""
        return self.filter(product=product)
    
    def with_products(self):
        """Optimize queries by selecting related products"""
        return self.select_related('product', 'order')
    
    def top_selling_products(self, limit=10, days=30):
        """Get top selling products"""
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days)
        
        return self.filter(
            order__created_at__gte=cutoff_date,
            order__payment_status='paid'
        ).values(
            'product__name',
            'product__sku'
        ).annotate(
            total_quantity=models.Sum('quantity'),
            total_revenue=models.Sum('line_total')
        ).order_by('-total_quantity')[:limit]


class OrderStatusHistoryManager(models.Manager):
    """Manager for OrderStatusHistory model"""
    
    def for_order(self, order):
        """Get status history for specific order"""
        return self.filter(order=order).order_by('created_at')
    
    def recent_changes(self, days=7):
        """Get recent status changes"""
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=cutoff_date)
    
    def by_user(self, user):
        """Get status changes made by specific user"""
        return self.filter(changed_by=user)
