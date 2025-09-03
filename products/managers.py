# products/managers.py
from django.db import models


class ProductManager(models.Manager):
    def active(self):
        """Get active products only."""
        return self.filter(is_active=True)
    
    def available(self):
        """Get active products with stock."""
        return self.filter(is_active=True, quantity__gt=0)
    
    def recommended(self):
        """Get recommended active products."""
        return self.filter(recommended=True, is_active=True)

    def discounted(self):
        """Get products with any type of discount."""
        return self.filter(is_active=True).filter(
            models.Q(discount_percent__gt=0) | models.Q(discount_per_unit__gt=0)
        )
    
    def with_category(self):
        """Optimize category queries."""
        return self.select_related('category')
    
    def with_related_data(self):
        """Optimize queries for product detail page."""
        return self.select_related('category').prefetch_related(
            'related_products',
            'category__parent'
        )
    
    def get_related_products(self, product, limit=6):
        """Get related products for a specific product."""
        return product.related_products.filter(
            is_active=True, 
            quantity__gt=0
        )[:limit]
    
    def get_category_breadcrumbs(self, category):
        """Generate category breadcrumbs."""
        breadcrumbs = []
        current = category
        while current:
            breadcrumbs.insert(0, current)
            current = current.parent
        return breadcrumbs
