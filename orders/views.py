from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from products.models import Product
from .cart import Cart
from .forms import CartAddForm
from .models import Order, OrderItem

class CartView(View):
    def get(self, request):
        cart = Cart(request)
        return render(request, 'orders/cart.html', {'cart': cart})

class CartAddView(PermissionRequiredMixin, View):
    permission_required = 'orders.add_order'
    
    def post(self, request, product_id):
        cart = Cart(request)
        product = get_object_or_404(Product, id=product_id)
        form = CartAddForm(request.POST)
        
        if form.is_valid():
            cart.add(product, form.cleaned_data['quantity'])
            messages.success(request, f"محصول {product.name} به سبد خرید اضافه شد")
        else:
            messages.error(request, "مشکل در افزودن محصول به سبد خرید")
        
        return redirect('orders:cart')

class CartRemoveView(View):
    def get(self, request, product_id):
        cart = Cart(request)
        product = get_object_or_404(Product, id=product_id)
        
        if cart.remove(product):
            messages.success(request, f"محصول {product.name} از سبد خرید حذف شد")
        else:
            messages.error(request, "محصول مورد نظر در سبد خرید یافت نشد")
        
        return redirect('orders:cart')

# Keep login required ONLY for checkout and order management
class OrderCreateView(LoginRequiredMixin, View):  # Login required HERE
    def get(self, request):
        cart = Cart(request)
        if len(cart) == 0:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'سبد خرید شما خالی است',
                    'redirect_url': '/products/'
                })
            messages.error(request, "سبد خرید شما خالی است")
            return redirect('products:product_list')

        # Stock validation before checkout
        for item in cart:
            if item['quantity'] > item['product'].quantity:
                error_msg = f"موجودی {item['product'].name} کافی نمی‌باشد"
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': error_msg
                    })
                messages.error(request, error_msg)
                return redirect('orders:cart')

        # Create order logic...
        try:
            with transaction.atomic():
                order = Order.objects.create(user=request.user)
                
                for item in cart:
                    product = item['product']
                    line = OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        product_sku=product.sku,
                        unit_price=product.unit_price,
                        quantity=item['quantity'],
                        discount_percent=product.discount_percent,
                        discount_per_unit=product.discount_per_unit,
                    )
                    line.recompute()
                    line.save()

                order.recalc_totals()
                order.save()
                cart.clear()

                success_msg = "سفارش شما با موفقیت ثبت شد"
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': success_msg,
                        'order_id': order.id,
                        'redirect_url': f'/orders/{order.id}/'
                    })
                
                messages.success(request, success_msg)
                return redirect('orders:order_detail', order.id)
                
        except Exception as e:
            error_msg = "خطا در ایجاد سفارش. لطفاً دوباره تلاش کنید."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                })
            messages.error(request, error_msg)
            return redirect('orders:cart')

class OrderDetailView(LoginRequiredMixin, View):
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        if order.user != request.user:
            raise Http404("سفارش یافت نشد")
        return render(request, 'orders/order.html', {'order': order})

class OrderDeleteView(LoginRequiredMixin, View):
    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        
        if order.user != request.user:
            return JsonResponse({'success': False, 'error': 'دسترسی غیرمجاز'}, status=403)

        if order.status == Order.Status.PAID:
            return JsonResponse({'success': False, 'error': 'نمی‌توانید سفارش پرداخت شده را حذف کنید'}, status=400)

        order.delete()
        return JsonResponse({'success': True})
