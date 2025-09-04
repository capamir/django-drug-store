# orders/forms.py
from django import forms
from django.core.exceptions import ValidationError

class CartAddForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
        
        # Set max value based on available stock
        if self.product:
            self.fields['quantity'].widget.attrs['max'] = str(self.product.quantity)
    
    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        
        if self.product:
            # Check product availability
            if not self.product.is_available:
                raise ValidationError(f"محصول '{self.product.name}' در حال حاضر موجود نمی‌باشد")
            
            # Check stock availability (basic check - cart will do final validation)
            if quantity > self.product.quantity:
                raise ValidationError(f"حداکثر موجودی: {self.product.quantity}")
        
        return quantity
