# /modular_store_backend/modules/error_handlers/__init__.py
from flask import Flask

from .handlers import init_error_handlers


def create_error_handlers(app: Flask) -> None:
    init_error_handlers(app)


# Expose necessary functions if needed
__all__ = ['create_error_handlers']
