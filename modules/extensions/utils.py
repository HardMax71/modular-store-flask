from flask_login import current_user

from config import AppConfig
from modules.db.database import db


def get_locale() -> str:
    if current_user.is_authenticated:
        return current_user.language
    return AppConfig.DEFAULT_LANG


def load_user(user_id):
    from modules.db.models import User
    user = User.query.get(user_id)
    if user:
        db.session.refresh(user)
    return user
