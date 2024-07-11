import gettext
import logging
from datetime import datetime
from typing import Any, Dict

from flask import Flask, redirect, url_for, g
from flask import session as flask_session
from flask_login import current_user
from werkzeug.wrappers.response import Response

from config import AppConfig
from modules import init_modules
from modules.db.database import db
from modules.db.models import Cart, Notification
from modules.error_handlers import create_error_handlers
from modules.extensions import init_extensions
from modules.logger import DatabaseLogger

# Initialize logger
logger = logging.getLogger(__name__)

# Configure gettext for internationalization
gettext.bindtextdomain(AppConfig.GETTEXT_DOMAIN, localedir=AppConfig.LOCALE_PATH)
gettext.textdomain(AppConfig.GETTEXT_DOMAIN)
_ = gettext.gettext


def create_app(config_class: Any=None) -> Flask:
    """
    Create and configure the Flask application.

    :param config_class: Configuration class for the app
    :return: Configured Flask app instance
    """
    current_app = Flask(__name__)
    if config_class:
        current_app.config.from_object(config_class)
    else:
        current_app.config.from_object(AppConfig)

    db.init_app(current_app)

    with current_app.app_context():
        db.init_db()
        DatabaseLogger(current_app)
        init_extensions(current_app)
        create_error_handlers(current_app)
        init_modules(current_app)
        register_request_handlers(current_app)

    return current_app


def register_request_handlers(current_app: Flask) -> None:
    """
    Register request lifecycle handlers for the app.

    :param current_app: Flask app instance
    """

    @current_app.before_request
    def before_request() -> None:
        """
        Handler for tasks to run before each request.
        """
        flask_session.permanent = True
        g.permanent_session_lifetime = AppConfig.PERMANENT_SESSION_LIFETIME
        flask_session.modified = True
        g.total_items, g.total_amount, g.discount_percentage = Cart.cart_info()

        if current_user.is_authenticated:
            g.mini_cart_items = db.session.query(Cart).filter_by(user_id=current_user.id).all()
            g.unread_notifications_count = db.session.query(Notification).filter_by(
                user_id=current_user.id, read=False
            ).count()
        else:
            g.mini_cart_items = []
            g.unread_notifications_count = 0

    @current_app.context_processor
    def inject_cart_info() -> Dict[str, Any]:
        """
        Inject cart information into the context for rendering templates.

        :return: Dictionary with cart information
        """
        return {
            "total_items": g.get('total_items', 0),
            "total_amount": g.get('total_amount', 0),
            "discount_percentage": g.get('discount_percentage', 0),
            "mini_cart_items": g.get('mini_cart_items', []),
            "unread_notifications_count": g.get('unread_notifications_count', 0)
        }

    @current_app.after_request
    def after_request(response: Response) -> Response:
        """
        Handler for tasks to run after each request.

        :param response: Response object
        :return: Modified response object
        """
        if 'last_active' in flask_session:
            last_active = datetime.fromisoformat(flask_session['last_active'])
            if (datetime.now() - last_active) > AppConfig.PERMANENT_SESSION_LIFETIME:
                db.session.remove()
                flask_session.clear()
                return redirect(url_for('auth.login'))
        flask_session['last_active'] = datetime.now().isoformat()

        # Set security headers
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        return response


if __name__ == "__main__":
    app = create_app()  # was before init
    app.run()
