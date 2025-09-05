# orders/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_items_display', 'subtotal_display', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'user__phone_number')
    readonly_fields = ('created_at', 'updated_at')
    
    def total_items_display(self, obj):
        return obj.total_items
    total_items_display.short_description = 'تعداد اقلام'
    
    def subtotal_display(self, obj):
        return f"{obj.subtotal_price:,} ریال"
    subtotal_display.short_description = 'جمع کل'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart_user', 'product', 'quantity', 'line_total_display', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('product__name', 'product__sku', 'cart__user__username', 'cart__user__phone_number')
    readonly_fields = ('created_at', 'updated_at')
    
    def cart_user(self, obj):
        return obj.cart.user.get_full_name() or obj.cart.user.phone_number
    cart_user.short_description = 'کاربر'
    
    def line_total_display(self, obj):
        return f"{obj.line_total:,} ریال"
    line_total_display.short_description = 'قیمت کل'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('line_total', 'created_at')
    fields = ('product', 'product_name', 'quantity', 'unit_price', 'discount_amount', 'line_total')


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('previous_status', 'new_status', 'changed_by', 'notes', 'created_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user_display', 'status_display', 'payment_status_display', 
                   'total_amount_display', 'created_at')
    list_filter = ('status', 'payment_status', 'created_at', 'updated_at')
    search_fields = ('order_number', 'user__username', 'user__email', 'user__phone_number', 
                    'customer_name', 'customer_phone')
    readonly_fields = ('order_number', 'created_at', 'updated_at', 'confirmed_at', 
                      'shipped_at', 'delivered_at')  # Fixed: removed 'subtotal_display'
    
    fieldsets = (
        ('اطلاعات سفارش', {
            'fields': ('order_number', 'user', 'status', 'payment_status')
        }),
        ('اطلاعات مالی', {
            'fields': ('subtotal', 'discount_amount', 'shipping_cost', 'total_amount')
        }),
        ('اطلاعات مشتری', {
            'fields': ('customer_name', 'customer_phone')
        }),
        ('آدرس ارسال', {
            'fields': ('shipping_address',),
            'classes': ('collapse',)
        }),
        ('یادداشت‌ها', {
            'fields': ('customer_notes', 'admin_notes'),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at', 'confirmed_at', 'shipped_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    
    def user_display(self, obj):
        return obj.user.get_full_name() or obj.user.phone_number
    user_display.short_description = 'کاربر'
    
    def status_display(self, obj):
        colors = {
            'pending': 'orange',
            'confirmed': 'blue', 
            'preparing': 'purple',
            'shipped': 'teal',
            'delivered': 'green',
            'cancelled': 'red',
            'returned': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'وضعیت سفارش'
    
    def payment_status_display(self, obj):
        colors = {
            'pending': 'orange',
            'paid': 'green',
            'failed': 'red',
            'refunded': 'gray'
        }
        color = colors.get(obj.payment_status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_payment_status_display()
        )
    payment_status_display.short_description = 'وضعیت پرداخت'
    
    def total_amount_display(self, obj):
        return f"{obj.total_amount:,} ریال"
    total_amount_display.short_description = 'مبلغ کل'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'product_name', 'quantity', 'unit_price_display', 
                   'discount_amount_display', 'line_total_display', 'created_at')
    list_filter = ('created_at', 'order__status', 'order__payment_status')
    search_fields = ('order__order_number', 'product__name', 'product__sku', 'product_name', 'product_sku')
    readonly_fields = ('line_total', 'created_at')  # Fixed: use actual field name
    
    def order_number(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.pk])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_number.short_description = 'شماره سفارش'
    
    def unit_price_display(self, obj):
        return f"{obj.unit_price:,} ریال"
    unit_price_display.short_description = 'قیمت واحد'
    
    def discount_amount_display(self, obj):
        return f"{obj.discount_amount:,} ریال"
    discount_amount_display.short_description = 'تخفیف'
    
    def line_total_display(self, obj):
        return f"{obj.line_total:,} ریال"
    line_total_display.short_description = 'قیمت کل'


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'previous_status', 'new_status_display', 'changed_by', 'created_at')
    list_filter = ('new_status', 'created_at')
    search_fields = ('order__order_number', 'changed_by__username', 'notes')
    readonly_fields = ('created_at',)
    
    def order_number(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.pk])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_number.short_description = 'شماره سفارش'
    
    def new_status_display(self, obj):
        colors = {
            'pending': 'orange',
            'confirmed': 'blue',
            'preparing': 'purple', 
            'shipped': 'teal',
            'delivered': 'green',
            'cancelled': 'red',
            'returned': 'gray'
        }
        color = colors.get(obj.new_status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, dict(Order.ORDER_STATUS_CHOICES).get(obj.new_status, obj.new_status)
        )
    new_status_display.short_description = 'وضعیت جدید'


# Additional admin configurations
admin.site.site_header = "مدیریت فروشگاه دارو"
admin.site.site_title = "پنل مدیریت"
admin.site.index_title = "خوش آمدید به پنل مدیریت فروشگاه"
