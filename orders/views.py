# orders/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, View
from django.db import transaction
from django.urls import reverse_lazy
from decimal import Decimal
from django.utils import timezone
from django.http import JsonResponse

from products.models import Product
from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory


class AddToCartView(LoginRequiredMixin, View):
    """Add product to user's shopping cart"""
    
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id, is_active=True)
        quantity = int(request.POST.get('quantity', 1))
        
        # Validate product availability and stock
        if not product.is_available:
            messages.error(request, f'محصول "{product.name}" در حال حاضر موجود نیست.')
            return redirect('products:product_detail', slug=product.slug)
        
        if quantity > product.quantity:
            messages.error(
                request, 
                f'تنها {product.quantity} عدد از "{product.name}" موجود است.'
            )
            return redirect('products:product_detail', slug=product.slug)
        
        if quantity < 1:
            messages.error(request, 'تعداد محصول باید حداقل 1 باشد.')
            return redirect('products:product_detail', slug=product.slug)
        
        # Get or create cart for user
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Get or create cart item
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not item_created:
            # Update existing item
            new_quantity = cart_item.quantity + quantity
            
            # Ensure we don't exceed stock
            if new_quantity > product.quantity:
                messages.warning(
                    request,
                    f'حداکثر {product.quantity} عدد از این محصول قابل سفارش است. تعداد به {product.quantity} تنظیم شد.'
                )
                cart_item.quantity = product.quantity
            else:
                cart_item.quantity = new_quantity
                
            cart_item.save()
            messages.success(
                request,
                f'{quantity} عدد از "{product.name}" به سبد خرید اضافه شد. (مجموع: {cart_item.quantity})'
            )
        else:
            messages.success(
                request,
                f'"{product.name}" با موفقیت به سبد خرید اضافه شد.'
            )
        
        return redirect('orders:cart_detail')

class CartDetailView(LoginRequiredMixin, DetailView):
    """Display user's cart contents"""
    
    model = Cart
    template_name = 'orders/cart_detail.html'
    context_object_name = 'cart'
    
    def get_object(self, queryset=None):
        """Get or create cart for user"""
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        print(f"Cart created: {created}, Cart ID: {cart.id}")
        return cart
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart = self.get_object()
        
        # Get cart items with product data
        cart_items = cart.items.select_related('product')
        
        # DEBUG: Print cart items count
        print(f"Cart items count: {cart_items.count()}")
        for item in cart_items:
            print(f"Item: {item.product.name}, Quantity: {item.quantity}")
        
        # Clean up unavailable items
        self.cleanup_unavailable_items(cart_items)
        
        # Refresh cart items after cleanup
        cart_items = cart.items.select_related('product')
        print(f"Cart items after cleanup: {cart_items.count()}")
        
        # Calculate cart totals
        cart_totals = self.calculate_cart_totals(cart_items)
        
        context.update({
            'cart_items': cart_items,
            'cart_totals': cart_totals,
            'has_items': cart_items.exists(),
        })
        
        return context
    
    def cleanup_unavailable_items(self, cart_items):
        """Remove unavailable items from cart"""
        unavailable_items = []
        for item in cart_items:
            if not item.product.is_available:
                unavailable_items.append(item)
        
        for item in unavailable_items:
            messages.warning(
                self.request,
                f'محصول "{item.product.name}" از سبد خرید حذف شد چون موجود نیست.'
            )
            item.delete()
    
    def calculate_cart_totals(self, cart_items):
        """Calculate cart financial totals"""
        subtotal = Decimal('0')
        total_discount = Decimal('0')
        total_items = 0
        
        for item in cart_items:
            item_subtotal = item.product.unit_price * item.quantity
            item_discount = Decimal('0')
            
            # Calculate discount if product has discount
            if item.product.has_discount:
                item_effective_price = item.product.effective_unit_price
                item_discount = (item.product.unit_price - item_effective_price) * item.quantity
            
            subtotal += item_subtotal
            total_discount += item_discount
            total_items += item.quantity
        
        # Calculate shipping
        shipping_cost = Decimal('25000') if subtotal < Decimal('500000') else Decimal('0')
        final_total = subtotal - total_discount + shipping_cost
        
        return {
            'subtotal': subtotal,
            'discount_amount': total_discount,
            'shipping_cost': shipping_cost,
            'total_amount': final_total,
            'total_items': total_items,
            'has_discount': total_discount > 0,
        }

class UpdateCartItemView(LoginRequiredMixin, View):
    """Update quantity of cart item"""
    
    def post(self, request, item_id):
        cart_item = get_object_or_404(
            CartItem,
            id=item_id,
            cart__user=request.user
        )
        
        new_quantity = int(request.POST.get('quantity', 1))
        
        # Validate quantity
        if new_quantity < 1:
            messages.error(request, 'تعداد محصول باید حداقل 1 باشد.')
            return redirect('orders:cart_detail')
        
        if new_quantity > cart_item.product.quantity:
            messages.error(
                request,
                f'تنها {cart_item.product.quantity} عدد از "{cart_item.product.name}" موجود است.'
            )
            return redirect('orders:cart_detail')
        
        # Update quantity
        cart_item.quantity = new_quantity
        cart_item.save()
        
        messages.success(
            request,
            f'تعداد "{cart_item.product.name}" به {new_quantity} عدد تغییر یافت.'
        )
        
        return redirect('orders:cart_detail')
