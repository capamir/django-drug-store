# orders/admin.py
from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = (
        'product_name',
        'product_sku',
        'unit_price',
        'quantity',
        'discount_percent',
        'discount_per_unit',
        'line_subtotal_amount',
        'line_discount_amount',
        'line_total_amount',
    )
    readonly_fields = (
        'product_name',
        'product_sku',
        'unit_price',
        'discount_percent',
        'discount_per_unit',
        'line_subtotal_amount',
        'line_discount_amount',
        'line_total_amount',
    )
    can_delete = False
    show_change_link = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'status', 'created', 'updated',
        'subtotal_amount', 'discount_amount', 'payable_amount', 'paid_at',
    )
    list_filter = ('status', 'created', 'paid_at')
    search_fields = ('user__phone_number', 'user__first_name', 'user__last_name', 'id')
    date_hierarchy = 'created'
    ordering = ('-created',)
    readonly_fields = ('subtotal_amount', 'discount_amount', 'payable_amount', 'paid_at', 'payment_authority', 'payment_ref_id')

    inlines = [OrderItemInline]

    fieldsets = (
        (None, {
            'fields': ('user', 'status', 'created', 'updated', 'paid_at')
        }),
        ('Payment Info', {
            'fields': ('payment_authority', 'payment_ref_id'),
        }),
        ('Totals', {
            'fields': ('subtotal_amount', 'discount_amount', 'payable_amount'),
        }),
    )

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'order', 'product_name', 'product_sku',
        'unit_price', 'quantity', 'discount_percent',
        'discount_per_unit', 'line_subtotal_amount',
        'line_discount_amount', 'line_total_amount',
    )
    list_filter = ('order',)
    search_fields = ('product_name', 'product_sku', 'order__id')
    readonly_fields = (
        'product_name', 'product_sku', 'unit_price',
        'discount_percent', 'discount_per_unit',
        'line_subtotal_amount', 'line_discount_amount',
        'line_total_amount',
    )
    ordering = ('order', 'id')
