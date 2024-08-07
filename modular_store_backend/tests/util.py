# /modular_store_backend/tests/util.py
import random

from werkzeug.security import generate_password_hash

from modular_store_backend.modules.db.models import User


def create_user(self,
                username: str = None,
                email: str = None,
                password: str = None,
                is_admin: bool = False,
                language: str = 'en'):
    if username is None:
        username = f'user_{random.randint(0, 123456)}'
    if email is None:
        email = f'{random.randint(0, 123456)}@example.com'
    if password is None:
        password = f'password_{random.randint(0, 123456)}'

    hashed_password = generate_password_hash(password)
    user = User(username=username, email=email, password=hashed_password,
                is_admin=is_admin, language=language)
    self.session.add(user)
    self.session.commit()
    return user
