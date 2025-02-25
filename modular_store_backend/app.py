# /modular_store_backend/app.py
import logging
import os
from datetime import datetime
from datetime import timedelta
from typing import Any

import yaml
from flask import Flask, redirect, url_for, g, flash
from flask.typing import ResponseValue
from flask_babel import gettext as _
from flask_login import current_user, logout_user
from werkzeug.wrappers.response import Response

from modular_store_backend.modules import init_modules
from modular_store_backend.modules.db.database import db
from modular_store_backend.modules.db.models import Cart, Notification
from modular_store_backend.modules.error_handlers import create_error_handlers
from modular_store_backend.modules.extensions import init_extensions
from modular_store_backend.modules.logger import DatabaseLogger


def load_config(config_path: str) -> Any:
    try:
        with open(config_path, 'r', encoding='utf-8') as config_file:
            config = yaml.safe_load(config_file)

        if 'PERMANENT_SESSION_LIFETIME' in config:
            minutes = int(config['PERMANENT_SESSION_LIFETIME'].split()[0])
            config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=minutes)

        return config
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML configuration: {e}")
        raise


def create_app(config_path: str = './modular_store_backend/config.yaml', config: Any = None) -> Flask:
    if config is None:
        config = load_config(config_path)

    current_app = Flask(__name__,
                        template_folder=os.path.abspath(config.get('TEMPLATE_FOLDER')),
                        static_folder=os.path.abspath(config.get('STATIC_FOLDER')))

    current_app.config.update(config)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

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
    def inject_cart_info() -> dict[str, Any]:
        return {
            "total_items": g.get('total_items', 0),
            "total_amount": g.get('total_amount', 0),
            "discount_percentage": g.get('discount_percentage', 0),
            "mini_cart_items": g.get('mini_cart_items', []),
            "unread_notifications_count": g.get('unread_notifications_count', 0)
        }

    @current_app.after_request
    def after_request(response: Response) -> ResponseValue:
        if current_user.is_authenticated:
            current_user.last_seen = datetime.utcnow()
            db.session.commit()
            if current_user.is_session_expired(current_app.config['PERMANENT_SESSION_LIFETIME']):
                logout_user()
                db.session.remove()
                flash(_("Your session has expired. Please log in again."), "warning")
                return redirect(url_for('auth.login'))

        # Set security headers
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        return response


if __name__ == "__main__":
    app = create_app()
    app.run()
