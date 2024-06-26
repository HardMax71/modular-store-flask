from apscheduler.schedulers.background import BackgroundScheduler
from flask_babel import Babel
from flask_dance.contrib.facebook import make_facebook_blueprint
from flask_dance.contrib.google import make_google_blueprint
from flask_login import LoginManager
from flask_login import current_user
from flask_mail import Mail

from config import AppConfig
from modules.cache import cache
from modules.db.backup import backup_database
from modules.db.database import db_session

babel = Babel()
login_manager = LoginManager()
mail = Mail()
scheduler = BackgroundScheduler()


def get_locale() -> str:
    if current_user.is_authenticated:
        return current_user.language
    return AppConfig.DEFAULT_LANG


def init_extensions(app):
    babel.init_app(app, locale_selector=get_locale)
    login_manager.init_app(app)
    mail.init_app(app)
    cache.init_app(app)

    # Set up scheduler
    scheduler.add_job(backup_database, 'interval', minutes=30, args=[app.config['BACKUP_DIR']])
    scheduler.start()

    # Register Flask-Dance blueprints
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

    @login_manager.user_loader
    def load_user(user_id):
        from modules.db.models import User
        user = User.query.get(user_id)
        if user:
            db_session.refresh(user)
        return user
