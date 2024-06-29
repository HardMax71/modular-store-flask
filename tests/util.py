# tests/utils.py
import random

from werkzeug.security import generate_password_hash

from modules.db.models import User


def create_user(self, username: str = None, email: str = None, password: str = None):
    if username is None:
        username = f'user_{random.randint(0, 123456)}'
    if email is None:
        email = f'{random.randint(0, 123456)}@example.com'
    if password is None:
        password = f'password_{random.randint(0, 123456)}'

    hashed_password = generate_password_hash(password)
    user = User(username=username, email=email, password=hashed_password)
    self.session.add(user)
    self.session.commit()
    return user
