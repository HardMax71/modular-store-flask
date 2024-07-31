# /modular_store_backend/modules/auth/__init__.py
from flask import Flask
from flask_limiter import Limiter

from modular_store_backend.modules.auth.views import init_auth


def create_auth_routes(app: Flask, limiter: Limiter) -> None:
    """
    Initialize authentication routes with rate limiting.

    :param app: Flask application instance
    :param limiter: Flask-Limiter instance for rate limiting
    """
    init_auth(app, limiter)


__all__ = ['create_auth_routes']
