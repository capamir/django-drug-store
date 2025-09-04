from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic.edit import FormView
from django.urls import reverse_lazy

from products.models import Product
from .cart import Cart
from .forms import CartAddForm
from .models import Order, OrderItem

class CartView(View):
    """
    Cart display view with AJAX-first approach.
    """
    
    def get(self, request):
        cart = Cart(request)
        
        # AJAX requests get JSON data
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                **cart.to_json()
            })
        
        # Regular requests get template with minimal data
        return render(request, 'orders/cart.html', {
            'cart_count': len(cart),
            'has_items': len(cart.cart) > 0,
        })

class CartOperationView(LoginRequiredMixin, View):
    """
    Unified AJAX cart operations view.
    Handles add, remove, and update quantity operations.
    """
    
    def post(self, request, product_id):
        """Handle cart operations based on 'action' parameter."""
        product = get_object_or_404(Product, id=product_id)
        cart = Cart(request)
        action = request.POST.get('action', '').lower()
        
        if action == 'add':
            return self._handle_add(request, cart, product)
        elif action == 'remove':
            return self._handle_remove(request, cart, product)
        elif action == 'update':
            return self._handle_update(request, cart, product)
        else:
            return JsonResponse({
                'success': False,
                'error': 'عملیات مشخص نشده است'
            })
    
    def _handle_add(self, request, cart, product):
        """Handle add to cart operation."""
        form = CartAddForm(request.POST, product=product)
        
        if form.is_valid():
            try:
                quantity = form.cleaned_data['quantity']
                cart.add(product, quantity)
                
                cart_data = cart.to_json()
                return JsonResponse({
                    'success': True,
                    'message': f"محصول {product.name} به سبد خرید اضافه شد",
                    'action': 'add',
                    'product_id': product.id,
                    'product_in_cart': True,
                    'product_cart_quantity': cart.get_product_quantity(product),
                    'stock_status': product.get_stock_status(),
                    'cart_count': cart_data['count'],
                    'cart_totals': cart_data['totals'],
                })
            except ValueError as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e),
                    'stock_status': product.get_stock_status(),
                    'available_quantity': product.quantity,
                })
        
        return JsonResponse({
            'success': False,
            'error': 'اطلاعات ارسالی نادرست است',
            'form_errors': form.errors,
        })
    
    def _handle_remove(self, request, cart, product):
        """Handle remove from cart operation."""
        if not cart.is_product_in_cart(product):
            return JsonResponse({
                'success': False,
                'error': f"محصول {product.name} در سبد خرید یافت نشد"
            })
        
        cart.remove(product)
        cart_data = cart.to_json()
        
        return JsonResponse({
            'success': True,
            'message': f"محصول {product.name} از سبد خرید حذف شد",
            'action': 'remove',
            'removed_product_id': product.id,
            'product_in_cart': False,
            'cart_count': cart_data['count'],
            'cart_totals': cart_data['totals'],
            'cart_has_items': cart_data['has_items'],
        })
    
    def _handle_update(self, request, cart, product):
        """Handle update quantity operation."""
        try:
            new_quantity = int(request.POST.get('quantity', 0))
            cart.update_quantity(product, new_quantity)
            
            cart_data = cart.to_json()
            return JsonResponse({
                'success': True,
                'message': f'تعداد محصول {product.name} به‌روزرسانی شد',
                'action': 'update',
                'product_id': product.id,
                'product_cart_quantity': new_quantity,
                'cart_count': cart_data['count'],
                'cart_totals': cart_data['totals'],
                'stock_status': product.get_stock_status(),
            })
        except (ValueError, TypeError) as e:
            return JsonResponse({
                'success': False,
                'error': str(e) if isinstance(e, ValueError) else 'تعداد وارد شده نامعتبر است',
                'available_quantity': product.quantity,
                'stock_status': product.get_stock_status(),
            })


class OrderDetailView(LoginRequiredMixin, View):
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        if order.user != request.user:
            raise Http404("سفارش یافت نشد")
        return render(request, 'orders/order.html', {'order': order})

class OrderCreateView(LoginRequiredMixin, View):
    def get(self, request):
        cart = Cart(request)
        if len(cart) == 0:
            messages.error(request, "سبد خرید شما خالی است")
            return redirect('products:product_list')

        # Check stock again before creating order
        for item in cart:
            if item['quantity'] > item['product'].quantity:
                messages.error(request, f"موجودی {item['product'].name} کافی نمی‌باشد")
                return redirect('orders:cart')

        with transaction.atomic():
            order = Order.objects.create(user=request.user)
            for item in cart:
                product = item['product']
                unit_price = product.unit_price
                discount_percent = product.discount_percent
                discount_per_unit = product.discount_per_unit

                line = OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    product_sku=product.sku,
                    unit_price=unit_price,
                    quantity=item['quantity'],
                    discount_percent=discount_percent,
                    discount_per_unit=discount_per_unit,
                )
                line.recompute()
                line.save()
            order.recalc_totals()
            order.save()
            cart.clear()
            messages.success(request, "سفارش شما با موفقیت ثبت شد")
        return redirect('orders:order_detail', order.id)


class OrderDeleteView(LoginRequiredMixin, View):
    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)

        # Permission check
        if order.user != request.user:
            return JsonResponse({'success': False, 'error': 'دسترسی غیرمجاز'}, status=403)

        # Only allow deleting orders that are not paid (optional business rule)
        if order.status == Order.Status.PAID:
            return JsonResponse({'success': False, 'error': 'نمی‌توانید سفارش پرداخت شده را حذف کنید'}, status=400)

        order.delete()
        return JsonResponse({'success': True})
