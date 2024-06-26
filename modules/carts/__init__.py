from flask import Flask

from .views import init_cart, add_to_cart, apply_discount_code


def create_cart_routes(app: Flask) -> None:
    init_cart(app)
