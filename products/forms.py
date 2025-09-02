from django import forms
from .models import Product, Category
from django.core.exceptions import ValidationError

class ProductForm(forms.ModelForm):
    """
    Comprehensive form for product creation and updates with proper validation.
    """
    
    class Meta:
        model = Product
        fields = [
            'name', 'slug', 'description', 'category', 
            'unit_price', 'cost_price', 'quantity', 'reorder_level',
            'sku', 'barcode', 'discount_percent', 'discount_per_unit',
            'image', 'is_active', 'recommended'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'dir': 'rtl',
                'placeholder': 'نام محصول'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control', 
                'dir': 'ltr',
                'placeholder': 'product-slug'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'dir': 'rtl',
                'rows': 4,
                'placeholder': 'توضیحات محصول'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1'
            }),
            'cost_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'reorder_level': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'sku': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'ltr',
                'placeholder': 'PRD001'
            }),
            'barcode': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'ltr'
            }),
            'discount_percent': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100'
            }),
            'discount_per_unit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'recommended': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def clean_sku(self):
        """Ensure SKU is unique"""
        sku = self.cleaned_data.get('sku')
        if sku:
            # Check for existing SKU excluding current instance
            existing = Product.objects.filter(sku=sku)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('محصولی با این کد SKU قبلاً ثبت شده است')
        return sku

    def clean_unit_price(self):
        """Validate unit price"""
        unit_price = self.cleaned_data.get('unit_price')
        if unit_price and unit_price <= 0:
            raise ValidationError('قیمت باید بیشتر از صفر باشد')
        return unit_price

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        unit_price = cleaned_data.get('unit_price')
        cost_price = cleaned_data.get('cost_price')
        
        # Warning if cost price is higher than unit price
        if unit_price and cost_price and cost_price > unit_price:
            raise ValidationError(
                'قیمت تمام شده نباید بیشتر از قیمت فروش باشد'
            )
        
        return cleaned_data

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug', 'description', 'parent', 'image', 'is_active']
