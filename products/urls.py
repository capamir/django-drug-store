from django.urls import path, include
from .views import admin_products, admin_categories, public_views

app_name = 'products'

# Admin Product URLs
admin_product_patterns = [
    path('products/', admin_products.AdminProductListView.as_view(), name='admin_product_list'),
    path('products/<int:product_id>/', admin_products.AdminProductDetailView.as_view(), name='admin_product_detail'),
    path('products/create/', admin_products.AdminProductCreateView.as_view(), name='admin_product_create'),
    path('products/<int:product_id>/edit/', admin_products.AdminProductUpdateView.as_view(), name='admin_product_edit'),
    path('products/<int:product_id>/delete/', admin_products.AdminProductDeleteView.as_view(), name='admin_product_delete'),
]

# Admin Category URLs
admin_category_patterns = [
    path('categories/', admin_categories.AdminCategoryListView.as_view(), name='admin_category_list'),
    path('categories/<int:category_id>/toggle/', admin_categories.AdminCategoryToggleView.as_view(), name='admin_category_toggle'),
]

urlpatterns = [
    # Product CRUD
    path('', public_views.HomeView.as_view(), name='home'),
    path('products/', public_views.ProductListView.as_view(), name='product_list'),
    path('<slug:slug>/', public_views.ProductDetailView.as_view(), name='product_detail'),
    
    # Admin routes - grouped under dashboard/
    path('dashboard/', include(admin_product_patterns)),
    path('dashboard/', include(admin_category_patterns)),
]
