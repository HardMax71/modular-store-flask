import random
import unittest

from flask import request
from flask_login import login_user, logout_user
from werkzeug.datastructures import LanguageAccept

from app import create_app
from config import AppConfig
from modules.db.database import db
from modules.db.models import User
from modules.extensions.utils import get_locale, load_user


class TestExtensionsUnit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        AppConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        cls.app = create_app(AppConfig)
        cls.client = cls.app.test_client()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        db.init_db()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        cls.app_context.pop()

    def setUp(self):
        db.session.begin(nested=True)

    def tearDown(self):
        db.session.rollback()

    def test_get_locale_authenticated(self):
        with self.app.test_request_context():
            user = User(username=f'user_{random.randint(0, 123456)}',
                        email=f'{random.randint(0, 123456)}@example.com',
                        password=f'password_{random.randint(0, 123456)}',
                        language='fr')
            db.session.add(user)
            db.session.commit()

            login_user(user)
            self.assertEqual(get_locale(), 'fr')
            logout_user()

    def test_get_locale_unauthenticated(self):
        with self.app.test_request_context():
            # Simulate an Accept-Language header
            request.accept_languages = LanguageAccept([('en', 1), ('ru', 0.8)])
            self.assertEqual(get_locale(), 'en')  # Cause default language is 'en'

            # Test with a non-supported language
            request.accept_languages = LanguageAccept([('fr', 1), ('de', 0.8)])
            self.assertEqual(get_locale(), AppConfig.DEFAULT_LANG)  # Should fall back to default

    def test_load_user(self):
        user = User(username=f'user_{random.randint(0, 123456)}',
                    email=f'{random.randint(0, 123456)}@example.com',
                    password=f'password_{random.randint(0, 123456)}')
        db.session.add(user)
        db.session.commit()

        loaded_user = load_user(user.id)
        self.assertEqual(loaded_user, user)

    def test_load_user_not_found(self):
        non_existent_id = 9999  # Assuming this ID doesn't exist
        loaded_user = load_user(non_existent_id)
        self.assertIsNone(loaded_user)


if __name__ == '__main__':
    unittest.main()
