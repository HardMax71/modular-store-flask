import gettext
import logging
from datetime import datetime

from flask import Flask
from flask import redirect, url_for, g, session
from flask_login import current_user

from config import AppConfig
from extensions import init_extensions
from modules import init_modules
from modules.db.database import init_db
from modules.db.models import db_session, Cart, Notification
from modules.error_handlers import create_error_handlers
from modules.logger import DatabaseLogger
from modules.main import main_bp

logger = logging.getLogger(__name__)

gettext.bindtextdomain(AppConfig.GETTEXT_DOMAIN, localedir=AppConfig.LOCALE_PATH)
gettext.textdomain(AppConfig.GETTEXT_DOMAIN)

_ = gettext.gettext


def create_app(config_class=AppConfig):
    current_app = Flask(__name__)
    current_app.config.from_object(config_class)

    # Initialize database
    init_db()

    # Set up logging
    DatabaseLogger(current_app)

    # Initialize extensions
    init_extensions(current_app)

    # Set up error handling
    create_error_handlers(current_app)

    # Register blueprints and initialize modules
    init_modules(current_app)
    current_app.register_blueprint(main_bp)

    # Register request handlers
    register_request_handlers(current_app)

    return current_app


def register_request_handlers(current_app):
    @current_app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

    @current_app.before_request
    def before_request():
        db_session.permanent = True
        g.permanent_session_lifetime = AppConfig.PERMANENT_SESSION_LIFETIME
        db_session.modified = True
        g.total_items, g.total_amount, g.discount_percentage = Cart.cart_info()

        if current_user.is_authenticated:
            g.mini_cart_items = Cart.query.filter_by(user_id=current_user.id).all()
            g.unread_notifications_count = Notification.query.filter_by(user_id=current_user.id,
                                                                        read=False).count()
        else:
            g.mini_cart_items = []
            g.unread_notifications_count = 0

    @current_app.context_processor
    def inject_cart_info():
        return {
            "total_items": g.get('total_items', 0),
            "total_amount": g.get('total_amount', 0),
            "discount_percentage": g.get('discount_percentage', 0),
            "mini_cart_items": g.get('mini_cart_items', []),
            "unread_notifications_count": g.get('unread_notifications_count', 0)
        }

    @current_app.after_request
    def after_request(response):
        if 'last_active' in session:
            last_active = datetime.fromisoformat(session['last_active'])
            if (datetime.now() - last_active) > AppConfig.PERMANENT_SESSION_LIFETIME:
                db_session.remove()
                session.clear()
                return redirect(url_for('auth.login'))
        session['last_active'] = datetime.now().isoformat()

        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        return response


app = create_app()

if __name__ == "__main__":
    app.run()
