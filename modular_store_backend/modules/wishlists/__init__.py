from flask import Flask

from modular_store_backend.modules.wishlists.utils import (
    get_product_selection_options,
    item_exists_in_wishlist,
    remove_item_from_wishlist,
    add_item_to_wishlist
)
from modular_store_backend.modules.wishlists.views import init_wishlist


def create_wishlist_routes(app: Flask) -> None:
    init_wishlist(app)


# Expose necessary functions
__all__ = [
    'create_wishlist_routes',
    'get_product_selection_options',
    'item_exists_in_wishlist',
    'remove_item_from_wishlist',
    'add_item_to_wishlist'
]
