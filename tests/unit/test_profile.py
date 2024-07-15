import unittest
from unittest.mock import patch, MagicMock

from flask import url_for
from flask_login import login_user

from modules.db.models import User, SocialAccount
from modules.profile.utils import (
    handle_profile_update, handle_change_email, handle_change_password, handle_change_phone,
    handle_update_profile, handle_change_language, handle_update_notification_settings,
    handle_social_login
)
from tests.base_test import BaseTest
from tests.util import create_user


class TestProfileUtils(BaseTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=True, define_load_user=True)

    def test_handle_profile_update_invalid_request(self):
        user = create_user(self)
        with self.app.test_request_context(data={'invalid_action': 'true'}):
            login_user(user)
            with patch('modules.profile.utils.flash') as mock_flash:
                handle_profile_update()
                mock_flash.assert_called_with('Invalid request.', 'danger')

    def test_handle_change_email_success(self):
        user = create_user(self)
        with self.app.test_request_context(data={'email': 'new@example.com'}):
            login_user(user)
            handle_change_email()
            updated_user = self.session.get(User, user.id)
            self.assertEqual(updated_user.email, 'new@example.com')

    def test_handle_change_email_already_in_use(self):
        user1 = create_user(self, email='user1@example.com')
        _ = create_user(self, email='user2@example.com')
        with self.app.test_request_context(data={'email': 'user2@example.com'}):
            login_user(user1)
            with patch('modules.profile.utils.flash') as mock_flash:
                handle_change_email()
                mock_flash.assert_called_with('This email is already in use.', 'warning')

    def test_handle_change_email_same_email(self):
        user = create_user(self, email='user@example.com')
        with self.app.test_request_context(data={'email': 'user@example.com'}):
            login_user(user)
            with patch('modules.profile.utils.flash') as mock_flash:
                handle_change_email()
                mock_flash.assert_called_with('New email is either empty or same as previous one.', 'warning')

    def test_handle_change_password_success(self):
        start_password = 'password'
        user = create_user(self, password=start_password)
        initial_password = user.password
        with self.app.test_request_context(data={
            'current_password': start_password,
            'new_password': 'newpassword',
            'confirm_password': 'newpassword'
        }):
            login_user(user)
            result = handle_change_password()
            updated_user = self.session.get(User, user.id)
            self.assertTrue(result)
            self.assertNotEqual(updated_user.password, initial_password)

    def test_handle_change_password_incorrect_current(self):
        user = create_user(self, password='password')
        with self.app.test_request_context(data={
            'current_password': 'wrongpassword',
            'new_password': 'newpassword',
            'confirm_password': 'newpassword'
        }):
            login_user(user)
            with patch('modules.profile.utils.flash') as mock_flash:
                result = handle_change_password()
                self.assertFalse(result)
                mock_flash.assert_called_with('Incorrect current password.', 'danger')

    def test_handle_change_password_mismatch(self):
        user = create_user(self, password='password')
        with self.app.test_request_context(data={
            'current_password': 'password',
            'new_password': 'newpassword1',
            'confirm_password': 'newpassword2'
        }):
            login_user(user)
            with patch('modules.profile.utils.flash') as mock_flash:
                result = handle_change_password()
                self.assertFalse(result)
                mock_flash.assert_called_with('The new password and confirmation do not match.', 'danger')

    def test_handle_change_phone_success(self):
        user = create_user(self, )
        with self.app.test_request_context(data={'phone': '+1 206 555 0100'}):
            login_user(user)
            handle_change_phone()
            updated_user = self.session.get(User, user.id)
            self.assertEqual(updated_user.phone, '+1 206 555 0100')

    def test_handle_change_phone_invalid(self):
        user = create_user(self, )
        with self.app.test_request_context(data={'phone': 'invalid_phone'}):
            login_user(user)
            with patch('modules.profile.utils.flash') as mock_flash:
                handle_change_phone()
                mock_flash.assert_called_with('Invalid phone number format.', 'danger')

    def test_handle_change_phone_same(self):
        user = create_user(self, )
        user.phone = '+1 206 555 0100'
        self.session.commit()
        with self.app.test_request_context(data={'phone': '+1 206 555 0100'}):
            login_user(user)
            with patch('modules.profile.utils.flash') as mock_flash:
                handle_change_phone()
                mock_flash.assert_called_with('The new phone number matches the current one or is empty.',
                                              'warning')

    def test_handle_update_profile(self):
        user = create_user(self, )
        with self.app.test_request_context(data={
            'fname': 'TestName',
            'lname': 'RRR',
            'phone': '123456782290',
            'files': {}
        }):
            login_user(user)

            handle_update_profile()
            updated_user = self.session.get(User, user.id)
            self.assertEqual(updated_user.fname, 'TestName')
            self.assertEqual(updated_user.lname, 'RRR')
            self.assertEqual(updated_user.phone, '123456782290')

    def test_handle_change_language(self):
        user = create_user(self, )
        with self.app.test_request_context(data={'language': 'fr'}):
            login_user(user)
            handle_change_language()
            updated_user = self.session.get(User, user.id)
            self.assertEqual(updated_user.language, 'fr')

    def test_handle_update_notification_settings(self):
        user = create_user(self, )
        with self.app.test_request_context(data={
            'notifications_enabled': 'on',
            'email_notifications_enabled': 'on'
        }):
            login_user(user)
            handle_update_notification_settings()
            updated_user = self.session.get(User, user.id)
            self.assertTrue(updated_user.notifications_enabled)
            self.assertTrue(updated_user.email_notifications_enabled)

    @patch('modules.profile.utils.redirect')
    def test_handle_social_login_connect_new_account(self, mock_redirect):
        with self.app.test_request_context():
            user = create_user(self, )
            login_user(user)  # Simulate logged-in user

            mock_provider = MagicMock()
            mock_provider.name = 'facebook'
            mock_provider.authorized = True
            mock_provider.token = {'access_token': 'new_access_token'}
            mock_provider.get.return_value.json.return_value = {
                'id': '12345',
                'name': 'John Doe',
                'email': 'john@example.com'
            }

            with patch('modules.profile.utils.flash') as mock_flash:
                handle_social_login(mock_provider, name='facebook')

                self.assertEqual(self.session.query(SocialAccount).count(), 1)
                new_social_account = self.session.query(SocialAccount).first()

                self.assertEqual(new_social_account.user_id, user.id)
                self.assertEqual(new_social_account.provider, 'facebook')
                self.assertEqual(new_social_account.social_id, '12345')
                self.assertEqual(new_social_account.access_token, 'new_access_token')

                mock_flash.assert_called_with('Facebook account successfully connected to your profile.', 'success')
                mock_redirect.assert_called_with(url_for('profile.profile_info'))

    @patch('modules.profile.utils.redirect')
    def test_handle_social_login_already_connected(self, mock_redirect):
        with self.app.test_request_context():
            user = create_user(self, )
            login_user(user)  # Simulate logged-in user

            # Create an existing social account for the user
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

            with patch('modules.profile.utils.flash') as mock_flash:
                handle_social_login(mock_provider, name='facebook')

                self.assertEqual(self.session.query(SocialAccount).count(), 1)  # No new account should be created

                mock_flash.assert_called_with('This Facebook account is already connected to your profile.', 'info')
                mock_redirect.assert_called_with(url_for('profile.profile_info'))


if __name__ == '__main__':
    unittest.main()
