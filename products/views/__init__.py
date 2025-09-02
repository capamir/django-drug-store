# Admin views
from .admin_products import (
    AdminProductListView, 
    AdminProductDetailView, 
    AdminProductCreateView, 
    AdminProductUpdateView,
    AdminProductDeleteView
)
from .admin_categories import (
    AdminCategoryListView,
    AdminCategoryToggleView
)

# Public views  
from .public_views import (
    HomeView,
    ProductListView,
    ProductDetailView,
)

# This allows: from products import views
# Then: views.AdminProductListView.as_view()

__all__ = [
    # Admin Product Views
    'AdminProductListView',
    'AdminProductDetailView', 
    'AdminProductCreateView',
    'AdminProductUpdateView',
    'AdminProductDeleteView',
    
    # Admin Category Views
    'AdminCategoryListView',
    'AdminCategoryToggleView',
    
    # # Public Views
    'HomeView',
    'ProductListView',
    'ProductDetailView',
]
