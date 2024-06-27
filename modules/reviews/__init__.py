from flask import Flask

from .utils import has_purchased
from .views import init_reviews


def create_reviews_routes(app: Flask) -> None:
    init_reviews(app)


# Expose necessary functions
__all__ = ['create_reviews_routes', 'has_purchased']
