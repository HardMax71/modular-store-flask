# /modular_store_backend/modules/__init__.py
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from modular_store_backend.modules.admin import create_admin
from modular_store_backend.modules.auth import create_auth_routes
from modular_store_backend.modules.carts import create_cart_routes
from modular_store_backend.modules.compare import create_compare_routes
from modular_store_backend.modules.filter import create_filter_routes
from modular_store_backend.modules.main import create_main_routes
from modular_store_backend.modules.profile import create_profile_routes
from modular_store_backend.modules.purchase_history import create_purchase_history_routes
from modular_store_backend.modules.reviews import create_reviews_routes
from modular_store_backend.modules.tickets import create_ticket_routes
from modular_store_backend.modules.wishlists import create_wishlist_routes


def init_modules(app: Flask) -> None:
    """
    Initialize all application modules and their routes with rate limiting.

    :param app: Flask application instance
    """
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[app.config['DEFAULT_LIMIT_RATE']],
        storage_uri=app.config['LIMITER_STORAGE_URI'] or "memory://"
    )

    create_main_routes(app)
    create_admin(app)
    create_auth_routes(app, limiter)
    create_cart_routes(app)
    create_purchase_history_routes(app)
    create_filter_routes(app)
    create_wishlist_routes(app)
    create_reviews_routes(app)
    create_compare_routes(app)
    create_ticket_routes(app)
    create_profile_routes(app)
