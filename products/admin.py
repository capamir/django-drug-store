from django.contrib import admin
from .models import Category, Product, StockMovement, ProductImage

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(StockMovement)
admin.site.register(ProductImage)
