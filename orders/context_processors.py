# orders/context_processors.py
from .cart import Cart

def cart(request):
    """
    Cart context processor for templates.
    Provides basic cart information without heavy computation.
    """
    cart = Cart(request)
    return {
        'cart': cart,
        'cart_count': len(cart),
        'cart_has_items': len(cart.cart) > 0,
    }
