from flask import Flask

from .utils import (
    get_variant_options,
    wishlist_exists,
    remove_from_wishlist,
    add_wishlist_item
)
from .views import init_wishlist


def create_wishlist_routes(app: Flask) -> None:
    init_wishlist(app)


# Expose necessary functions
__all__ = [
    'create_wishlist_routes',
    'get_variant_options',
    'wishlist_exists',
    'remove_from_wishlist',
    'add_wishlist_item'
]
