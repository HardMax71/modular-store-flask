# /modular_store_backend/modules/carts/__init__.py
from flask import Flask

from modular_store_backend.modules.carts.views import init_cart
from modular_store_backend.modules.carts.utils import apply_discount_code, add_to_cart


def create_cart_routes(app: Flask) -> None:
    init_cart(app)


__all__ = ['create_cart_routes', 'add_to_cart', 'apply_discount_code']
