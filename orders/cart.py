from products.models import Product  # Updated import

CART_SESSION_ID = 'cart'

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_ID)
        if not cart:
            cart = self.session[CART_SESSION_ID] = {}
        self.cart = cart

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        cart = self.cart.copy()
        for product in products:
            cart[str(product.id)]['product'] = product
        for item in cart.values():
            item['total_price'] = int(item['price']) * item['quantity']
            yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def add(self, product, quantity):
        product_id = str(product.id)
        current_quantity = self.cart.get(product_id, {}).get('quantity', 0)
        new_total = current_quantity + quantity

        # Inventory check: Only add if enough stock
        if product.quantity < new_total:
            # Not enough stock! Don't add and raise or return an error message
            raise ValueError(f"موجودی کافی برای '{product.name}' وجود ندارد. حداکثر موجودی: {product.quantity}")

        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0, 'price': str(product.unit_price)}  # Use unit_price for accuracy

        self.cart[product_id]['quantity'] = new_total
        self.save()

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def save(self):
        self.session.modified = True

    def get_total_price(self):
        return sum(int(item['price']) * item['quantity'] for item in self.cart.values())

    def clear(self):
        del self.session[CART_SESSION_ID]
        self.save()
