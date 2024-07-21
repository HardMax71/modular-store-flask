from typing import Optional

from flask import request, current_app
from flask_login import current_user
from werkzeug.datastructures import LanguageAccept

from modular_store_backend.modules.db.database import db
from modular_store_backend.modules.db.models import User


def get_locale() -> str:
    if current_user.is_authenticated:
        return current_user.language or str(current_app.config['DEFAULT_LANG'])

    accept_languages: LanguageAccept = request.accept_languages or LanguageAccept()
    best_match: str | None = accept_languages.best_match(current_app.config['LANGUAGES'])

    return best_match or str(current_app.config['DEFAULT_LANG'])


def load_user(user_id: int) -> Optional[User]:
    user: Optional[User] = db.session.get(User, user_id)
    if user:
        db.session.refresh(user)
    return user
