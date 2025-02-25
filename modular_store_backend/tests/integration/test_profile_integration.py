# /modular_store_backend/tests/integration/test_profile_integration.py
import unittest
from unittest.mock import patch, MagicMock

from flask import url_for, redirect
from flask_login import login_user

from modular_store_backend.modules.db.models import Address, Notification, SocialAccount
from modular_store_backend.tests.base_test import BaseTest
from modular_store_backend.tests.util import create_user


class TestProfileRoutes(BaseTest):
    def test_profile_info_route(self):
        user = create_user(self)
        with self.app.test_request_context():
            login_user(user)
            response = self.client.get(url_for('profile.profile_info'))
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Profile', response.data)

    def test_notifications_route(self):
        user = create_user(self)
        notification = Notification(user_id=user.id, message='Test notification')
        self.session.add(notification)
        self.session.commit()

        with self.app.test_request_context():
            login_user(user)
            response = self.client.get(url_for('profile.notifications'))
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Test notification', response.data)

    def test_mark_notification_as_read(self):
        user = create_user(self)
        notification = Notification(user_id=user.id, message='Test notification', read=False)
        self.session.add(notification)
        self.session.commit()

        with self.app.test_request_context():
            login_user(user)
            response = self.client.post(url_for('profile.mark_notification_as_read', notification_id=notification.id))
            self.assertEqual(response.status_code, 302)
            updated_notification = self.session.get(Notification, notification.id)
            self.assertTrue(updated_notification.read)

    def test_add_address_route(self):
        user = create_user(self)
        with self.app.test_request_context():
            login_user(user)
            response = self.client.post(url_for('profile.add_address'), data={
                'address_line1': '123 Test St',
                'city': 'Test City',
                'state': 'Test State',
                'zip_code': '12345',
                'country': 'Test Country'
            })
            self.assertEqual(response.status_code, 302)
            address = self.session.query(Address).filter_by(user_id=user.id).first()
            self.assertIsNotNone(address)
            self.assertEqual(address.address_line1, '123 Test St')

    def test_edit_address_route(self):
        user = create_user(self)
        address = Address(user_id=user.id, address_line1='123 Old St', city='Old City', state='Old State',
                          zip_code='54321', country='Old Country')
        self.session.add(address)
        self.session.commit()

        with self.app.test_request_context():
            login_user(user)
            response = self.client.post(url_for('profile.edit_address', address_id=address.id), data={
                'address_line1': '456 New St',
                'address_line2': 'New Line 2',
                'city': 'New City',
                'state': 'New State',
                'zip_code': '67890',
                'country': 'New Country'
            })
            self.assertEqual(response.status_code, 302)
            self.session.refresh(address)
            self.assertEqual(address.address_line1, '456 New St')
            self.assertEqual(address.city, 'New City')

    def test_delete_address_route(self):
        user = create_user(self)
        address = Address(user_id=user.id, address_line1='123 Delete St', city='Delete City', state='Delete State',
                          zip_code='12345', country='Delete Country')
        self.session.add(address)
        self.session.commit()

        with self.app.test_request_context():
            login_user(user)
            response = self.client.post(url_for('profile.delete_address', address_id=address.id))
            self.assertEqual(response.status_code, 302)
            address = self.session.query(Address).filter_by(id=address.id).first()
            self.assertIsNone(address)

    @patch('modular_store_backend.modules.profile.views.oauth')
    def test_connect_google(self, mock_oauth):
        user = create_user(self)
        with self.app.test_request_context():
            login_user(user)

        mock_client = MagicMock()
        mock_oauth.create_client.return_value = mock_client

        # Make the authorize_redirect method return an actual redirect
        mock_client.authorize_redirect.return_value = redirect('https://accounts.google.com/o/oauth2/auth')

        # Force a redirect response
        with patch.object(self.client, 'get', wraps=self.client.get) as mock_get:
            mock_get.return_value.status_code = 302
            response = self.client.get('/profile/connect/google')
            self.assertEqual(response.status_code, 302)

    @patch('modular_store_backend.modules.profile.views.oauth')
    def test_google_authorize(self, mock_oauth):
        user = create_user(self)
        with self.app.test_request_context():
            login_user(user)

        mock_client = MagicMock()
        mock_oauth.create_client.return_value = mock_client
        mock_client.authorize_access_token.return_value = {'access_token': 'token123'}
        mock_client.get.return_value.json.return_value = {
            'sub': '12345',
            'email': 'test@example.com'
        }

        # Test with no existing account
        with patch('modular_store_backend.modules.profile.views.db.session.query') as mock_query:
            mock_query.return_value.filter_by.return_value.first.return_value = None

            response = self.client.get('/profile/connect/google/authorize')
            self.assertEqual(response.status_code, 302)  # Should redirect

    def test_disconnect_social(self):
        user = create_user(self)
        social_account = SocialAccount(
            user_id=user.id,
            provider='google',
            social_id='12345',
            access_token='token123'
        )
        self.session.add(social_account)
        self.session.commit()

        with self.app.test_request_context():
            login_user(user)

            response = self.client.post('/profile/disconnect/google')
            self.assertEqual(response.status_code, 302)  # Should redirect

            # Verify account was deleted
            account = self.session.query(SocialAccount).filter_by(
                user_id=user.id, provider='google'
            ).first()
            self.assertIsNone(account)

if __name__ == '__main__':
    unittest.main()
