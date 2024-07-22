from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask_babel import Babel
from flask_login import LoginManager
from flask_mail import Mail

from modular_store_backend.modules.cache import cache
from modular_store_backend.modules.db.backup import backup_database
from modular_store_backend.modules.extensions.utils import get_locale, load_user
from modular_store_backend.modules.oauth_login import init_oauth

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
    scheduler.add_job(backup_database, 'interval', seconds=app.config['BACKUP_INTERVAL'], args=[app])
    if not scheduler.running:
        scheduler.start()

    # init OAuth
    init_oauth(app)

    login_manager.user_loader(load_user)


__all__ = ['init_extensions', 'get_locale', 'scheduler', 'babel', 'login_manager', 'mail', 'cache']
