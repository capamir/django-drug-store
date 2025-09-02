from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Product CRUD
    path('', views.HomeView.as_view(), name='home'),
    
    path('dashboard/products/', views.AdminProductListView.as_view(), name='admin_product_list'),
    path('dashboard/products/<int:product_id>/', views.AdminProductDetailView.as_view(), name='admin_product_detail'),
    path('dashboard/products/create/', views.AdminProductCreateView.as_view(), name='admin_product_create'),
    path('dashboard/products/<int:product_id>/edit/', views.AdminProductUpdateView.as_view(), name='admin_product_edit'),
    path('dashboard/products/<int:product_id>/delete/', views.AdminProductDeleteView.as_view(), name='admin_product_delete'),
    
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<slug:slug>/update/', views.ProductUpdateView.as_view(), name='product_update'),
    path('products/<slug:slug>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),

    # Category CRUD
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/<slug:slug>/', views.CategoryDetailView.as_view(), name='category_detail'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<slug:slug>/update/', views.CategoryUpdateView.as_view(), name='category_update'),
    path('categories/<slug:slug>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
]
