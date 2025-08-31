from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.http import JsonResponse
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

class CartAddView(LoginRequiredMixin, View):
    def post(self, request, product_id):
        cart = Cart(request)
        product = get_object_or_404(Product, id=product_id)
        form = CartAddForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            try:
                cart.add(product, quantity)
                messages.success(request, f"محصول {product.name} به سبد خرید اضافه شد")
            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'اطلاعات ارسالی نادرست است')
        return redirect('orders:cart')

class CartRemoveView(LoginRequiredMixin, View):
    def get(self, request, product_id):
        cart = Cart(request)
        product = get_object_or_404(Product, id=product_id)
        cart.remove(product)
        messages.info(request, f"محصول {product.name} از سبد خرید حذف شد")
        return redirect('orders:cart')

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
