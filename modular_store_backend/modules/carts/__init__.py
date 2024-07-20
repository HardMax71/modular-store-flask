from flask import Flask

from modular_store_backend.modules.carts.views import add_to_cart, init_cart
from modular_store_backend.modules.carts.utils import apply_discount_code


def create_cart_routes(app: Flask) -> None:
    init_cart(app)


__all__ = ['create_cart_routes', 'add_to_cart', 'apply_discount_code']
