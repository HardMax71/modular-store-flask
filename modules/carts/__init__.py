from flask import Flask

from .utils import add_to_cart, apply_discount_code
from .views import init_cart


def create_cart_routes(app: Flask) -> None:
    init_cart(app)


__all__ = ['create_cart_routes', 'add_to_cart', 'apply_discount_code']
