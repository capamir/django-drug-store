# orders/models.py
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from products.models import Product  # adjust to your app

User = get_user_model()

class Order(models.Model):
    class Status(models.TextChoices):
        CART = "cart", "Cart"
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        CANCELED = "canceled", "Canceled"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CART)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    # Monetary amounts in Iranian Rial (store as integers for exact math)
    subtotal_amount = models.BigIntegerField(default=0)        # sum of line (unit*qty) before discounts
    discount_amount = models.BigIntegerField(default=0)        # sum of line discounts
    shipping_amount = models.BigIntegerField(default=0)        # add if needed later
    payable_amount = models.BigIntegerField(default=0)         # subtotal - discount + shipping

    # Payment tracking (Zarinpal)
    payment_authority = models.CharField(max_length=64, blank=True)   # Zarinpal Authority
    payment_ref_id = models.CharField(max_length=64, blank=True)      # Zarinpal RefID after verify
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-updated", "-id")
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["created"]),
        ]

    def __str__(self):
        return f"Order #{self.pk} - {self.user}"

    def recalc_totals(self):
        lines = list(self.items.all())
        subtotal = sum(li.unit_price * li.quantity for li in lines)
        discount = sum(li.line_discount_amount for li in lines)
        self.subtotal_amount = int(subtotal)
        self.discount_amount = int(discount)
        self.payable_amount = int(subtotal - discount + self.shipping_amount)

    @transaction.atomic
    def mark_paid(self, authority=None, ref_id=None, paid_time=None):
        # Idempotent state transition: only act if not already PAID
        if self.status == Order.Status.PAID:
            return
        self.status = Order.Status.PAID
        self.paid_at = paid_time or timezone.now()
        if authority:
            self.payment_authority = authority
        if ref_id:
            self.payment_ref_id = ref_id
        self.save(update_fields=["status", "paid_at", "payment_authority", "payment_ref_id", "updated"])

        # Decrement inventory safely once paid
        for li in self.items.select_related("product").select_for_update():
            if li.product and li.product.quantity is not None:
                # Guard against negative inventory
                new_qty = max(0, li.product.quantity - li.quantity)
                li.product.quantity = new_qty
                li.product.save(update_fields=["quantity"])

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True)
    # Snapshot fields for audit/immutability
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=50)
    unit_price = models.BigIntegerField()  # price per unit at time of order (Rial)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    # Per-line discount model (percentage or absolute captured at order time)
    discount_percent = models.PositiveIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    discount_per_unit = models.BigIntegerField(default=0)  # optional absolute per-unit off in Rial

    # Denormalized totals for speed and auditing
    line_subtotal_amount = models.BigIntegerField(default=0)   # unit_price * qty
    line_discount_amount = models.BigIntegerField(default=0)   # computed from percent/absolute
    line_total_amount = models.BigIntegerField(default=0)      # subtotal - discount

    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order", "id")
        indexes = [
            models.Index(fields=["order"]),
        ]

    def __str__(self):
        return f"Item #{self.pk} of Order #{self.order_id}"

    def recompute(self):
        self.line_subtotal_amount = int(self.unit_price * self.quantity)
        percent_off = (self.discount_percent * self.unit_price) // 100 if self.discount_percent else 0
        per_unit_discount = max(percent_off, self.discount_per_unit)
        per_unit_discount = min(per_unit_discount, self.unit_price)  # prevent negative
        self.line_discount_amount = int(per_unit_discount * self.quantity)
        self.line_total_amount = int(self.line_subtotal_amount - self.line_discount_amount)
