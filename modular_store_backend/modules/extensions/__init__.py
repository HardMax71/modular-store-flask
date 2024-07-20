from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask_babel import Babel
from flask_dance.contrib.facebook import make_facebook_blueprint
from flask_dance.contrib.google import make_google_blueprint
from flask_login import LoginManager
from flask_mail import Mail

from modular_store_backend.modules.cache import cache
from modular_store_backend.modules.db.backup import backup_database
from modular_store_backend.modules.extensions.utils import get_locale, load_user

babel = Babel()
login_manager = LoginManager()
mail = Mail()
scheduler = BackgroundScheduler()


def init_extensions(app: Flask) -> None:
    """
    Initialize Flask extensions.

    :param app: Flask application instance
    """
    babel.init_app(app, locale_selector=get_locale)
    login_manager.init_app(app)
    mail.init_app(app)
    cache.init_app(app)

    # Set up scheduler
    scheduler.add_job(backup_database, 'interval', minutes=30, args=[app])
    if not scheduler.running:
        scheduler.start()

    # Register Flask-Dance blueprints for OAuth
    facebook_bp = make_facebook_blueprint(
        client_id=app.config['FACEBOOK_OAUTH_CLIENT_ID'],
        client_secret=app.config['FACEBOOK_OAUTH_CLIENT_SECRET'],
        scope='email',
        redirect_url='/facebook-login'
    )
    app.register_blueprint(facebook_bp, url_prefix='/facebook-login')

    google_bp = make_google_blueprint(
        client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
        client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
        scope=['profile', 'email'],
        redirect_url='/google-login'
    )
    app.register_blueprint(google_bp, url_prefix='/google-login')

    login_manager.user_loader(load_user)


__all__ = ['init_extensions', 'get_locale', 'scheduler', 'babel', 'login_manager', 'mail', 'cache']
