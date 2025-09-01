# products/managers.py
from django.db import models

class ProductManager(models.Manager):
    def recommended(self):
        return self.filter(recommended=True, is_active=True)

    def discounted(self):
        return self.filter(is_active=True).filter(
            models.Q(discount_percent__gt=0) | models.Q(discount_per_unit__gt=0)
        )
