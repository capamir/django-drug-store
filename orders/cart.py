from products.models import Product
from decimal import Decimal

CART_SESSION_ID = 'cart'

class Cart:
    """
    Session-based shopping cart optimized for AJAX interactions.
    Handles inventory validation, pricing calculations, and JSON serialization.
    """
    
    def __init__(self, request):
        """Initialize cart from session."""
        self.session = request.session
        cart = self.session.get(CART_SESSION_ID)
        if not cart:
            cart = self.session[CART_SESSION_ID] = {}
        self.cart = cart

    def __iter__(self):
        """Iterate over cart items with product objects attached."""
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        cart = self.cart.copy()
        
        # Attach product objects to cart items
        for product in products:
            cart[str(product.id)]['product'] = product

        for item in cart.values():
            yield item

    def __len__(self):
        """Return total quantity of items in cart."""
        return sum(item['quantity'] for item in self.cart.values())

    def add(self, product, quantity):
        """
        Add product to cart with inventory validation.
        
        Args:
            product: Product instance to add
            quantity: Quantity to add (int)
            
        Raises:
            ValueError: If insufficient stock available
        """
        if not product.is_available:
            raise ValueError(f"محصول '{product.name}' در حال حاضر موجود نمی‌باشد")
            
        product_id = str(product.id)
        current_quantity = self.cart.get(product_id, {}).get('quantity', 0)
        new_total = current_quantity + quantity

        if product.quantity < new_total:
            raise ValueError(f"موجودی کافی برای '{product.name}' وجود ندارد. حداکثر موجودی: {product.quantity}")

        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0, 
                'price': str(product.unit_price)
            }
        
        self.cart[product_id]['quantity'] = new_total
        self.save()

    def remove(self, product):
        """Remove product completely from cart."""
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()
            return True
        return False

    def update_quantity(self, product, quantity):
        """
        Update product quantity in cart with validation.
        
        Args:
            product: Product instance
            quantity: New quantity (int)
            
        Raises:
            ValueError: If insufficient stock or invalid quantity
        """
        if quantity < 1:
            raise ValueError("تعداد باید حداقل 1 باشد")
            
        if not product.is_available:
            raise ValueError(f"محصول '{product.name}' در حال حاضر موجود نمی‌باشد")
            
        if quantity > product.quantity:
            raise ValueError(f"موجودی کافی نمی‌باشد. حداکثر: {product.quantity}")
        
        product_id = str(product.id)
        if product_id in self.cart:
            self.cart[product_id]['quantity'] = quantity
            self.save()

    def get_product_quantity(self, product):
        """Get quantity of specific product in cart."""
        return self.cart.get(str(product.id), {}).get('quantity', 0)

    def is_product_in_cart(self, product):
        """Check if specific product is in cart."""
        return str(product.id) in self.cart

    def get_totals(self):
        """Calculate all cart totals and return as dictionary."""
        session_total = Decimal('0')
        effective_total = Decimal('0')
        total_savings = Decimal('0')
        
        for item in self:
            if 'product' not in item:
                continue
                
            product = item['product']
            quantity = item['quantity']
            
            # Session total (using stored prices)
            session_total += Decimal(str(item['price'])) * quantity
            
            # Effective total (current prices with discounts)
            line_effective = product.effective_unit_price * quantity
            effective_total += line_effective
            
            # Savings calculation
            line_original = product.unit_price * quantity
            total_savings += line_original - line_effective
        
        return {
            'session_total': float(session_total),
            'effective_total': float(effective_total),
            'original_total': float(effective_total + total_savings),
            'total_savings': float(total_savings),
        }

    def to_json(self):
        """
        Convert cart to JSON-ready dictionary for AJAX responses.
        Returns complete cart data optimized for frontend consumption.
        """
        cart_items = []
        
        for item in self:
            if 'product' not in item:
                continue
                
            product = item['product']
            quantity = item['quantity']
            
            # Calculate pricing
            unit_price = float(product.unit_price)
            effective_price = float(product.effective_unit_price)
            stored_price = float(item['price'])
            
            original_line_total = unit_price * quantity
            effective_line_total = effective_price * quantity
            line_savings = original_line_total - effective_line_total
            
            cart_items.append({
                'product_id': product.id,
                'product_name': product.name,
                'product_slug': product.slug,
                'product_image': product.image.url if product.image else None,
                'sku': product.sku,
                
                # Pricing
                'unit_price': unit_price,
                'effective_unit_price': effective_price,
                'stored_price': stored_price,
                'quantity': quantity,
                'original_line_total': original_line_total,
                'effective_line_total': effective_line_total,
                'line_savings': line_savings,
                
                # Discounts
                'has_discount': product.has_discount,
                'discount_percent': product.discount_percent,
                'discount_per_unit': float(product.discount_per_unit),
                
                # Stock
                'stock_status': product.get_stock_status(),
                'available_quantity': product.quantity,
                'is_available': product.is_available,
                'low_stock': product.low_stock,
            })

        totals = self.get_totals()
        
        return {
            'items': cart_items,
            'count': len(self),
            'item_count': len(self.cart),
            'has_items': len(self.cart) > 0,
            'totals': totals
        }

    def save(self):
        """Mark session as modified to ensure persistence."""
        self.session.modified = True

    def clear(self):
        """Clear all items from cart."""
        del self.session[CART_SESSION_ID]
        self.save()
