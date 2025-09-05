# orders/urls.py
from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Cart URLs
    path('cart/', views.CartDetailView.as_view(), name='cart_detail'),
    path('cart/add/<int:product_id>/', views.AddToCartView.as_view(), name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.UpdateCartItemView.as_view(), name='update_cart_item'),  
    path('cart/remove/<int:item_id>/', views.RemoveCartItemView.as_view(), name='remove_cart_item'), 
    path('cart/clear/', views.ClearCartView.as_view(), name='clear_cart'),
    
    # Checkout & Orders
    path('checkout/', views.CheckoutView.as_view(), name='checkout'), 
]
