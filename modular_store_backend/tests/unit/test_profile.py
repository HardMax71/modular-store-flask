# /modular_store_backend/tests/unit/test_profile.py
import unittest
from io import BytesIO

from flask import url_for
from flask_login import login_user

from modular_store_backend.modules.db.models import User, SocialAccount
from modular_store_backend.modules.profile.utils import (
    handle_profile_update, handle_change_email, handle_change_password, handle_change_phone,
    handle_update_profile, handle_change_language, handle_update_notification_settings,
    handle_social_login, validate_phone
)
from modular_store_backend.tests.base_test import BaseTest
from modular_store_backend.tests.util import create_user


class TestProfileUtils(BaseTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=True, define_load_user=True)

    def test_handle_profile_update_invalid_request(self):
        user = create_user(self)
        with self.app.test_request_context(data={'invalid_action': 'true'}):
            login_user(user)
            handle_profile_update()
            messages = self.get_flashed_messages_from_djinja_globals()
            self.assertIn('Invalid request.', messages)

    def test_handle_change_email_already_in_use(self):
        user1 = create_user(self, email='user1@example.com')
        _ = create_user(self, email='user2@example.com')
        with self.app.test_request_context(data={'email': 'user2@example.com'}):
            login_user(user1)
            handle_change_email()
            messages = self.get_flashed_messages_from_djinja_globals()
            self.assertIn('This email is already in use.', messages)

    def test_handle_change_email_same_email(self):
        user = create_user(self, email='user@example.com')
        with self.app.test_request_context(data={'email': 'user@example.com'}):
            login_user(user)
            handle_change_email()
            messages = self.get_flashed_messages_from_djinja_globals()
            self.assertIn('New email is either empty or same as previous one.', messages)

    def test_handle_change_email_success(self):
        user = create_user(self)
        with self.app.test_request_context(data={'email': 'new@example.com'}):
            login_user(user)
            handle_change_email()
            updated_user = self.session.get(User, user.id)
            self.assertEqual(updated_user.email, 'new@example.com')
            messages = self.get_flashed_messages_from_djinja_globals()
            self.assertIn('Email changed successfully.', messages)

    def test_handle_change_password_incorrect_current(self):
        user = create_user(self, password='password')
        with self.app.test_request_context(data={
            'current_password': 'wrongpassword',
            'new_password': 'newpassword',
            'confirm_password': 'newpassword'
        }):
            login_user(user)
            result = handle_change_password()
            self.assertFalse(result)
            messages = self.get_flashed_messages_from_djinja_globals()
            self.assertIn('Incorrect current password.', messages)

    def test_handle_change_password_mismatch(self):
        user = create_user(self, password='password')
        with self.app.test_request_context(data={
            'current_password': 'password',
            'new_password': 'newpassword1',
            'confirm_password': 'newpassword2'
        }):
            login_user(user)
            result = handle_change_password()
            self.assertFalse(result)
            messages = self.get_flashed_messages_from_djinja_globals()
            self.assertIn('The new password and confirmation do not match.', messages)

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
            messages = self.get_flashed_messages_from_djinja_globals()
            self.assertIn('Password changed successfully.', messages)

    def test_handle_change_phone_invalid(self):
        user = create_user(self)
        with self.app.test_request_context(data={'phone': 'invalid_phone'}):
            login_user(user)
            handle_change_phone()
            messages = self.get_flashed_messages_from_djinja_globals()
            self.assertIn('Invalid phone number format.', messages)

    def test_handle_change_phone_same(self):
        user = create_user(self)
        user.phone = '+1 206 555 0100'
        self.session.commit()
        with self.app.test_request_context(data={'phone': '+1 206 555 0100'}):
            login_user(user)
            handle_change_phone()
            messages = self.get_flashed_messages_from_djinja_globals()
            self.assertIn('The new phone number matches the current one or is empty.', messages)

    def test_handle_change_phone_success(self):
        user = create_user(self)
        with self.app.test_request_context(data={'phone': '+1 206 555 0100'}):
            login_user(user)
            handle_change_phone()
            updated_user = self.session.get(User, user.id)
            self.assertEqual(updated_user.phone, '+1 206 555 0100')
            messages = self.get_flashed_messages_from_djinja_globals()
            self.assertIn('Phone number successfully changed.', messages)

    def test_handle_update_profile(self):
        user = create_user(self)
        with self.app.test_request_context(data={
            'fname': 'TestName',
            'lname': 'RRR',
            'phone': '+1-418-543-8090',
            'files': {}
        }):
            login_user(user)
            handle_update_profile()
            updated_user = self.session.get(User, user.id)
            self.assertEqual(updated_user.fname, 'TestName')
            self.assertEqual(updated_user.lname, 'RRR')
            self.assertEqual(updated_user.phone, '+1-418-543-8090')
            messages = self.get_flashed_messages_from_djinja_globals()
            self.assertIn('Profile updated successfully.', messages)

    def test_handle_update_profile_invalid_phone(self):
        user = create_user(self)
        with self.app.test_request_context(data={
            'fname': 'TestName',
            'lname': 'RRR',
            'phone': 'invalid_phone',
            'files': {}
        }):
            login_user(user)
            handle_update_profile()
            messages = self.get_flashed_messages_from_djinja_globals()
            self.assertIn('Invalid phone number format.', messages)

    def test_handle_update_profile_invalid_file_type(self):
        user = create_user(self)
        with self.app.test_request_context():
            login_user(user)
            data = {
                'fname': 'TestName',
                'lname': 'RRR',
                'phone': '+1-418-543-8090',
                'update_profile': 'Update Profile',  # This simulates the submit button
                'profile_picture': (BytesIO(b"fake image data"), 'invalid_file.false')
            }
            response = self.client.post(url_for('profile.profile_info'),
                                        data=data,
                                        content_type='multipart/form-data')
            self.assertEqual(response.status_code, 200)
            self.assertIn('Invalid file type', response.data.decode())

    def test_handle_change_language(self):
        user = create_user(self)
        with self.app.test_request_context(data={'language': 'fr'}):
            login_user(user)
            handle_change_language()
            updated_user = self.session.get(User, user.id)
            self.assertEqual(updated_user.language, 'fr')
            messages = self.get_flashed_messages_from_djinja_globals()
            self.assertIn('Language changed successfully.', messages)

    def test_handle_update_notification_settings(self):
        user = create_user(self)
        with self.app.test_request_context(data={
            'notifications_enabled': 'on',
            'email_notifications_enabled': 'on'
        }):
            login_user(user)
            handle_update_notification_settings()
            updated_user = self.session.get(User, user.id)
            self.assertTrue(updated_user.notifications_enabled)
            self.assertTrue(updated_user.email_notifications_enabled)
            messages = self.get_flashed_messages_from_djinja_globals()
            self.assertIn('Notification settings updated successfully.', messages)

    def test_validate_phone_success(self):
        valid_phone = '+14155552671'
        self.assertTrue(validate_phone(valid_phone))

    def test_validate_phone_invalid(self):
        invalid_phone = 'invalid_phone'
        self.assertFalse(validate_phone(invalid_phone))

    def test_handle_social_login_connect_new_account(self):
        with self.app.test_request_context():
            user = create_user(self)
            login_user(user)  # Simulate logged-in user

            mock_provider = unittest.mock.MagicMock()
            mock_provider.name = 'facebook'
            mock_provider.authorized = True
            mock_provider.token = {'access_token': 'new_access_token'}
            mock_provider.get.return_value.json.return_value = {
                'id': '12345',
                'name': 'John Doe',
                'email': 'john@example.com'
            }

            handle_social_login(mock_provider, name='facebook')

            self.assertEqual(self.session.query(SocialAccount).count(), 1)
            new_social_account = self.session.query(SocialAccount).first()

            self.assertEqual(new_social_account.user_id, user.id)
            self.assertEqual(new_social_account.provider, 'facebook')
            self.assertEqual(new_social_account.social_id, '12345')
            self.assertEqual(new_social_account.access_token, 'new_access_token')

            messages = self.get_flashed_messages_from_djinja_globals()
            self.assertIn('Facebook account successfully connected to your profile.', messages)

    def test_handle_social_login_already_connected(self):
        with self.app.test_request_context():
            user = create_user(self)
            login_user(user)  # Simulate logged-in user

            # Create an existing social account for the user
            social_account = SocialAccount(user_id=user.id, provider='facebook', social_id='12345',
                                           access_token='existing_token')
            self.session.add(social_account)
            self.session.commit()

            mock_provider = unittest.mock.MagicMock()
            mock_provider.name = 'facebook'
            mock_provider.authorized = True
            mock_provider.token = {'access_token': 'new_access_token'}
            mock_provider.get.return_value.json.return_value = {
                'id': '12345',
                'name': 'John Doe',
                'email': 'john@example.com'
            }

            handle_social_login(mock_provider, name='facebook')

            self.assertEqual(self.session.query(SocialAccount).count(), 1)  # No new account should be created

            messages = self.get_flashed_messages_from_djinja_globals()
            self.assertIn('This Facebook account is already connected to your profile.', messages)


if __name__ == '__main__':
    unittest.main()
