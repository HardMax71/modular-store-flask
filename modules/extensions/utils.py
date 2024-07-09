from typing import Optional

from flask import request
from flask_login import current_user
from werkzeug.datastructures import LanguageAccept

from config import AppConfig
from modules.db.database import db
from modules.db.models import User  # Move this import to the top


def get_locale() -> str:
    if current_user.is_authenticated:
        return current_user.language or AppConfig.DEFAULT_LANG

    accept_languages = request.accept_languages or LanguageAccept()
    best_match = accept_languages.best_match(AppConfig.LANGUAGES)

    return best_match or AppConfig.DEFAULT_LANG


def load_user(user_id: int) -> Optional[User]:
    user: Optional[User] = db.session.get(User, user_id)
    if user:
        db.session.refresh(user)
    return user
