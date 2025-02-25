# /modular_store_backend/modules/purchase_history/__init__.py
from flask import Flask

from modular_store_backend.modules.purchase_history.utils import save_purchase_history
from modular_store_backend.modules.purchase_history.views import init_purchase_history


def create_purchase_history_routes(app: Flask) -> None:
    init_purchase_history(app)


# Expose necessary functions
__all__ = ['create_purchase_history_routes', 'save_purchase_history']
