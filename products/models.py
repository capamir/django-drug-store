# product/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='children'
    )
    image = models.ImageField(upload_to='category_images/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    unit_price = models.DecimalField(max_digits=12, decimal_places=0)  # Rial
    cost_price = models.DecimalField(max_digits=12, decimal_places=0)  # Rial
    quantity = models.PositiveIntegerField(default=0)  # inventory in units
    reorder_level = models.PositiveIntegerField(default=5)  # alert threshold
    sku = models.CharField(max_length=50, unique=True)
    barcode = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    discount_percent = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='تخفیف درصدی روی قیمت فروش (از 0 تا 100)'
    )
    discount_per_unit = models.BigIntegerField(
        default=0,
        help_text='تخفیف عددی ثابت به ازای هر واحد کالا (به ریال)'
    )

    @property
    def effective_unit_price(self):
        """Calculate discounted price based on discount_percent and discount_per_unit."""
        price_after_percent = self.unit_price * (100 - self.discount_percent) // 100
        price_after_discount = max(0, price_after_percent - self.discount_per_unit)
        return price_after_discount
    
    def __str__(self):
        return self.name

    @property
    def low_stock(self):
        return self.quantity <= self.reorder_level

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')
    is_default = models.BooleanField(default=False)


class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('adjustment', 'Adjustment'),
        ('loss', 'Loss')
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()
    before_quantity = models.IntegerField(editable=False)
    after_quantity = models.IntegerField(editable=False)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        self.before_quantity = self.product.quantity
        self.after_quantity = self.before_quantity + self.quantity
        super().save(*args, **kwargs)
        # update product quantity
        self.product.quantity = self.after_quantity
        self.product.save()
