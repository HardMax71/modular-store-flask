import unittest
import random
from unittest.mock import patch, MagicMock
from flask_login import LoginManager
from flask_login import login_user
from werkzeug.security import generate_password_hash, check_password_hash

from app import create_app
from config import AppConfig
from modules.db.database import db, Base
from modules.db.models import User, SocialAccount
from modules.profile.utils import (
    handle_profile_update, handle_change_email, handle_change_password, handle_change_phone,
    handle_update_profile, handle_change_language, handle_update_notification_settings,
    handle_social_login
)

class TestProfileUtils(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        AppConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        cls.app = create_app(AppConfig)
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.app.config['SERVER_NAME'] = 'localhost'  # Add this line
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        LoginManager().init_app(cls.app)

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()
        db.session.remove()
        db.engine.dispose()

    def setUp(self):
        self.client = self.app.test_client()
        self.session = db.session
        self.session.begin()

        # Clear all tables
        for table in reversed(Base.metadata.sorted_tables):
            self.session.execute(table.delete())
        self.session.commit()

    def tearDown(self):
        self.session.rollback()
        self.session.close()
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

    def test_handle_profile_update_invalid_request(self):
        user = self.create_user()
        with self.app.test_request_context(data={'invalid_action': 'true'}):
            with self.app.test_client():
                login_user(user)
                with patch('modules.profile.utils.flash') as mock_flash:
                    handle_profile_update()
                    mock_flash.assert_called_with('Invalid request.', 'danger')

    def test_handle_change_email_success(self):
        user = self.create_user()
        with self.app.test_request_context(data={'email': 'new@example.com'}):
            with self.app.test_client():
                login_user(user)
                handle_change_email()
                updated_user = self.session.get(User, user.id)
                self.assertEqual(updated_user.email, 'new@example.com')

    def test_handle_change_email_already_in_use(self):
        user1 = self.create_user(email='user1@example.com')
        user2 = self.create_user(email='user2@example.com')
        with self.app.test_request_context(data={'email': 'user2@example.com'}):
            with self.app.test_client():
                login_user(user1)
                with patch('modules.profile.utils.flash') as mock_flash:
                    handle_change_email()
                    mock_flash.assert_called_with('This email is already in use.', 'warning')

    def test_handle_change_email_same_email(self):
        user = self.create_user(email='user@example.com')
        with self.app.test_request_context(data={'email': 'user@example.com'}):
            with self.app.test_client():
                login_user(user)
                with patch('modules.profile.utils.flash') as mock_flash:
                    handle_change_email()
                    mock_flash.assert_called_with('New email is either empty or same as previous one.', 'warning')

    def test_handle_change_password_success(self):
        start_password = 'password'
        user = self.create_user(password=start_password)
        initial_password = user.password
        with self.app.test_request_context(data={
            'current_password': start_password,
            'new_password': 'newpassword',
            'confirm_password': 'newpassword'
        }):
            with self.app.test_client():
                login_user(user)
                result = handle_change_password()
                updated_user = self.session.get(User, user.id)
                self.assertTrue(result)
                self.assertNotEqual(updated_user.password, initial_password)

    def test_handle_change_password_incorrect_current(self):
        user = self.create_user(password='password')
        with self.app.test_request_context(data={
            'current_password': 'wrongpassword',
            'new_password': 'newpassword',
            'confirm_password': 'newpassword'
        }):
            with self.app.test_client():
                login_user(user)
                with patch('modules.profile.utils.flash') as mock_flash:
                    result = handle_change_password()
                    self.assertFalse(result)
                    mock_flash.assert_called_with('Incorrect current password.', 'danger')

    def test_handle_change_password_mismatch(self):
        user = self.create_user(password='password')
        with self.app.test_request_context(data={
            'current_password': 'password',
            'new_password': 'newpassword1',
            'confirm_password': 'newpassword2'
        }):
            with self.app.test_client():
                login_user(user)
                with patch('modules.profile.utils.flash') as mock_flash:
                    result = handle_change_password()
                    self.assertFalse(result)
                    mock_flash.assert_called_with('The new password and confirmation do not match.', 'danger')

    def test_handle_change_phone_success(self):
        user = self.create_user()
        with self.app.test_request_context(data={'phone': '+1 206 555 0100'}):
            with self.app.test_client():
                login_user(user)
                handle_change_phone()
                updated_user = self.session.get(User, user.id)
                self.assertEqual(updated_user.phone, '+1 206 555 0100')

    def test_handle_change_phone_invalid(self):
        user = self.create_user()
        with self.app.test_request_context(data={'phone': 'invalid_phone'}):
            with self.app.test_client():
                login_user(user)
                with patch('modules.profile.utils.flash') as mock_flash:
                    handle_change_phone()
                    mock_flash.assert_called_with('Invalid phone number format.', 'danger')

    def test_handle_change_phone_same(self):
        user = self.create_user()
        user.phone = '+1 206 555 0100'
        self.session.commit()
        with self.app.test_request_context(data={'phone': '+1 206 555 0100'}):
            with self.app.test_client():
                login_user(user)
                with patch('modules.profile.utils.flash') as mock_flash:
                    handle_change_phone()
                    mock_flash.assert_called_with('The new phone number matches the current one or is empty.', 'warning')

    def test_handle_update_profile(self):
        user = self.create_user()
        with self.app.test_request_context(data={
            'fname': 'TestName',
            'lname': 'RRR',
            'phone': '123456782290',
            'files': {}
        }):
            with self.app.test_client():
                login_user(user)

                handle_update_profile()
                updated_user = self.session.get(User, user.id)
                self.assertEqual(updated_user.fname, 'TestName')
                self.assertEqual(updated_user.lname, 'RRR')
                self.assertEqual(updated_user.phone, '123456782290')

    def test_handle_change_language(self):
        user = self.create_user()
        with self.app.test_request_context(data={'language': 'fr'}):
            with self.app.test_client():
                login_user(user)
                handle_change_language()
                updated_user = self.session.get(User, user.id)
                self.assertEqual(updated_user.language, 'fr')

    def test_handle_update_notification_settings(self):
        user = self.create_user()
        with self.app.test_request_context(data={
            'notifications_enabled': 'on',
            'email_notifications_enabled': 'on'
        }):
            with self.app.test_client():
                login_user(user)
                handle_update_notification_settings()
                updated_user = self.session.get(User, user.id)
                self.assertTrue(updated_user.notifications_enabled)
                self.assertTrue(updated_user.email_notifications_enabled)

    @patch('modules.profile.utils.redirect')
    @patch('modules.profile.utils.login_user')
    def test_handle_social_login_existing_user(self, mock_login_user, mock_redirect):
        with self.app.test_request_context():
            user = self.create_user()
            social_account = SocialAccount(user_id=user.id, provider='facebook', social_id='12345',
                                           access_token='existing_token')
            self.session.add(social_account)
            self.session.commit()

            mock_provider = MagicMock()
            mock_provider.name = 'facebook'
            mock_provider.authorized = True
            mock_provider.token = {'access_token': 'new_access_token'}
            mock_provider.get.return_value.json.return_value = {
                'id': '12345',
                'name': 'John Doe',
                'email': 'john@example.com'
            }

            handle_social_login(mock_provider)
            mock_login_user.assert_called_with(user)
            mock_redirect.assert_called()

    @patch('modules.profile.utils.redirect')
    @patch('modules.profile.utils.login_user')
    def test_handle_social_login_new_user(self, mock_login_user, mock_redirect):
        with self.app.test_request_context():
            mock_provider = MagicMock()
            mock_provider.name = 'facebook'
            mock_provider.authorized = True
            mock_provider.token = {'access_token': 'new_access_token'}
            mock_provider.get.return_value.json.return_value = {
                'id': '12345',
                'name': 'John Doe',
                'email': 'john@example.com'
            }

            handle_social_login(mock_provider)

            self.assertEqual(User.query.count(), 1)
            self.assertEqual(SocialAccount.query.count(), 1)

            new_user = User.query.first()
            new_social_account = SocialAccount.query.first()

            self.assertEqual(new_user.username, 'John Doe')
            self.assertEqual(new_user.email, 'john@example.com')
            self.assertEqual(new_social_account.provider, 'facebook')
            self.assertEqual(new_social_account.social_id, '12345')
            self.assertEqual(new_social_account.access_token, 'new_access_token')

            mock_login_user.assert_called_with(new_user)
            mock_redirect.assert_called()

if __name__ == '__main__':
    unittest.main()