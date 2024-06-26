from flask import Flask
from .views import init_purchase_history
from .utils import save_purchase_history


def create_purchase_history_routes(app: Flask) -> None:
    init_purchase_history(app)


# Expose necessary functions
__all__ = ['create_purchase_history_routes', 'save_purchase_history']
