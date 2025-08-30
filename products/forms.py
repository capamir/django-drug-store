from django import forms
from .models import Product, Category

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'slug', 'description', 'category', 'unit_price', 'cost_price', 'quantity', 'reorder_level', 'sku', 'barcode', 'is_active']

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug', 'description', 'parent', 'image', 'is_active']
