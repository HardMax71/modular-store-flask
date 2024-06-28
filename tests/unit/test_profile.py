import random
import unittest

from flask_login import LoginManager
from flask_login import login_user
from werkzeug.security import generate_password_hash

from app import create_app
from config import AppConfig
from modules.db.database import db
from modules.db.models import User
from modules.profile.utils import (
    handle_change_email, handle_change_password, handle_change_phone,
    handle_update_profile, handle_change_language, handle_update_notification_settings
)


class TestProfileUtils(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        AppConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        cls.app = create_app(AppConfig)
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False

        cls.app_context = cls.app.app_context()
        cls.app_context.push()

        LoginManager().init_app(cls.app)

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.engine.dispose()
        cls.app_context.pop()

    def setUp(self):
        self.client = self.app.test_client()
        self.session = db.session
        self.session.begin()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def create_user(self, username: str = None, email: str = None, password: str = None):
        # If parameters are None, generate random values
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

    def test_handle_change_email(self):
        user = self.create_user()
        with self.app.test_request_context(data={'email': 'new@example.com'}):
            with self.app.test_client() as c:
                login_user(user)
                handle_change_email()
                updated_user = User.query.get(user.id)
                self.assertEqual(updated_user.email, 'new@example.com')

    def test_handle_change_password(self):
        start_password = 'password'
        user = self.create_user(password=start_password)
        initial_password = user.password
        with self.app.test_request_context(data={
            'current_password': start_password,
            'new_password': 'newpassword',
            'confirm_password': 'newpassword'
        }):
            with self.app.test_client() as c:
                login_user(user)
                password_changed = handle_change_password()
                updated_user = User.query.get(user.id)
                self.assertTrue(password_changed, "Password change operation failed")
                self.assertNotEqual(updated_user.password, initial_password)

    def test_handle_change_phone(self):
        user = self.create_user()
        with self.app.test_request_context(data={'phone': '+1 206 555 0100'}):
            with self.app.test_client() as c:
                login_user(user)
                handle_change_phone()
                updated_user = User.query.get(user.id)
                self.assertEqual(updated_user.phone, '+1 206 555 0100')

    def test_handle_update_profile(self):
        user = self.create_user()
        with self.app.test_request_context(data={
            'fname': 'John',
            'lname': 'Doe',
            'phone': '1234567890'
        }, method='POST'):
            with self.app.test_client() as c:
                login_user(user)
                handle_update_profile()
                updated_user = User.query.get(user.id)
                self.assertEqual(updated_user.fname, 'John')
                self.assertEqual(updated_user.lname, 'Doe')
                self.assertEqual(updated_user.phone, '1234567890')

    def test_handle_change_language(self):
        user = self.create_user()
        with self.app.test_request_context(data={'language': 'fr'}):
            with self.app.test_client() as c:
                login_user(user)
                handle_change_language()
                updated_user = User.query.get(user.id)
                self.assertEqual(updated_user.language, 'fr')

    def test_handle_update_notification_settings(self):
        user = self.create_user()
        with self.app.test_request_context(data={
            'notifications_enabled': 'on',
            'email_notifications_enabled': 'on'
        }):
            with self.app.test_client() as c:
                login_user(user)
                handle_update_notification_settings()
                updated_user = User.query.get(user.id)
                self.assertTrue(updated_user.notifications_enabled)
                self.assertTrue(updated_user.email_notifications_enabled)


if __name__ == '__main__':
    unittest.main()
