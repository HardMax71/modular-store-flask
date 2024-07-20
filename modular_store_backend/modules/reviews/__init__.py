from flask import Flask

from modular_store_backend.modules.reviews.utils import has_purchased
from modular_store_backend.modules.reviews.views import init_reviews


def create_reviews_routes(app: Flask) -> None:
    init_reviews(app)


# Expose necessary functions
__all__ = ['create_reviews_routes', 'has_purchased']
