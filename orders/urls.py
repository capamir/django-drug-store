# orders/urls.py
from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Cart URLs
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/operation/<int:product_id>/', views.CartOperationView.as_view(), name='cart_operation'),
    
    # Order URLs
    path('create/', views.OrderCreateView.as_view(), name='order_create'),
    path('order/<int:order_id>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('order/<int:order_id>/delete/', views.OrderDeleteView.as_view(), name='order_delete'),
]
