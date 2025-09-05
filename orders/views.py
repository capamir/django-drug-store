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

class RemoveCartItemView(LoginRequiredMixin, View):
    """Remove item from cart completely"""
    
    def post(self, request, item_id):
        cart_item = get_object_or_404(
            CartItem,
            id=item_id,
            cart__user=request.user
        )
        
        product_name = cart_item.product.name
        cart_item.delete()
        
        messages.success(
            request,
            f'"{product_name}" از سبد خرید حذف شد.'
        )
        
        return redirect('orders:cart_detail')

class ClearCartView(LoginRequiredMixin, View):
    """Clear all items from user's cart"""
    
    def post(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        if cart.items.exists():
            items_count = cart.items.count()
            cart.clear()  # Uses the clear() method we defined in the Cart model
            
            messages.success(
                request,
                f'{items_count} محصول از سبد خرید حذف شد.'
            )
        else:
            messages.info(request, 'سبد خرید شما قبلاً خالی است.')
        
        return redirect('orders:cart_detail')


class CheckoutView(LoginRequiredMixin, View):
    """Convert cart to order"""
    
    def get(self, request):
        """Show checkout form"""
        cart = get_object_or_404(Cart, user=request.user)
        
        if cart.is_empty:
            messages.error(request, 'سبد خرید شما خالی است.')
            return redirect('orders:cart_detail')
        
        # Validate all cart items are still available
        unavailable_items = []
        for item in cart.items.all():
            if not item.product.is_available or item.quantity > item.product.quantity:
                unavailable_items.append(item)
        
        if unavailable_items:
            for item in unavailable_items:
                messages.warning(
                    request,
                    f'محصول "{item.product.name}" دیگر موجود نیست و از سبد خرید حذف شد.'
                )
                item.delete()
            return redirect('orders:cart_detail')
        
        # Calculate cart totals for display
        cart_totals = self.calculate_checkout_totals(cart)
        
        context = {
            'cart': cart,
            'cart_items': cart.items.select_related('product'),
            'cart_totals': cart_totals,
            'user_addresses': request.user.addresses.filter(is_active=True),
            'default_address': request.user.get_default_address(),
        }
        
        return render(request, 'orders/checkout.html', context)
    
    def post(self, request):
        """Process order creation from cart"""
        cart = get_object_or_404(Cart, user=request.user)
        
        if cart.is_empty:
            messages.error(request, 'سبد خرید شما خالی است.')
            return redirect('orders:cart_detail')
        
        # Get form data
        address_id = request.POST.get('address_id')
        customer_notes = request.POST.get('customer_notes', '')
        
        if not address_id:
            messages.error(request, 'لطفاً آدرس ارسال را انتخاب کنید.')
            return redirect('orders:checkout')
        
        try:
            address = request.user.addresses.get(id=address_id, is_active=True)
            shipping_address = {
                'title': address.title,
                'full_address': address.get_full_address(),
                'recipient_name': address.recipient_name,
                'recipient_phone': address.recipient_phone,
                'postal_code': address.postal_code,
            }
        except:
            messages.error(request, 'آدرس انتخاب شده معتبر نیست.')
            return redirect('orders:checkout')
        
        try:
            with transaction.atomic():
                # Calculate totals
                cart_totals = self.calculate_checkout_totals(cart)
                
                # Create order
                order = Order.objects.create(
                    user=request.user,
                    cart=cart,
                    subtotal=cart_totals['subtotal'],
                    discount_amount=cart_totals['discount_amount'],
                    shipping_cost=cart_totals['shipping_cost'],
                    total_amount=cart_totals['total_amount'],
                    shipping_address=shipping_address,
                    customer_notes=customer_notes,
                    status='pending',
                    payment_status='pending'
                )
                
                # Create order items from cart items
                for cart_item in cart.items.all():
                    # Final stock validation
                    if cart_item.quantity > cart_item.product.quantity:
                        raise ValueError(f'موجودی {cart_item.product.name} کافی نیست.')
                    
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
                
                # Create status history
                OrderStatusHistory.objects.create(
                    order=order,
                    new_status='pending',
                    changed_by=request.user,
                    notes='سفارش ایجاد شد'
                )
                
                # Clear cart
                cart.clear()
                
                messages.success(
                    request,
                    f'سفارش شما با شماره {order.order_number} ثبت شد.'
                )
                
                return redirect('orders:order_detail', order_number=order.order_number)
                
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('orders:checkout')
        except Exception as e:
            messages.error(request, 'خطا در ثبت سفارش. لطفاً دوباره تلاش کنید.')
            return redirect('orders:checkout')
    
    def calculate_checkout_totals(self, cart):
        """Calculate totals for checkout display"""
        subtotal = cart.subtotal_price
        discount_amount = cart.get_total_discount()
        shipping_cost = Decimal('25000') if subtotal < Decimal('500000') else Decimal('0')
        total_amount = subtotal + shipping_cost
        
        return {
            'subtotal': subtotal,
            'discount_amount': discount_amount,
            'shipping_cost': shipping_cost,
            'total_amount': total_amount,
            'total_items': cart.total_items,
        }
