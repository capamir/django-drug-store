from django import forms

class CartAddForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        max_value=25,  
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'inputmode': 'numeric',
            'aria-label': 'تعداد'
        })
    )
    product_id = forms.IntegerField(widget=forms.HiddenInput())
