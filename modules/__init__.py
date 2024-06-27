from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .admin import create_admin
from .auth import create_auth_routes
from .carts import create_cart_routes
from .compare import create_compare_routes
from .filter import create_filter_routes
from .profile import create_profile_routes
from .purchase_history import create_purchase_history_routes
from .reviews import create_reviews_routes
from .tickets import create_ticket_routes
from .wishlists import create_wishlist_routes


def init_modules(app):
    limiter = Limiter(app=app, key_func=get_remote_address, default_limits=[app.config['DEFAULT_LIMIT_RATE']],
                      storage_uri="memory://")

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
