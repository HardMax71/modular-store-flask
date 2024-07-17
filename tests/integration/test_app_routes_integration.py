import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from app import create_app
from config import AppConfig
from modules.db.models import User
from tests.base_test import BaseTest


class TestAppRoutes(BaseTest):
    @classmethod
    def setUpClass(cls):
        # Patch the scheduler.start() method
        cls.scheduler_patch = patch('modules.extensions.scheduler.start')
        cls.scheduler_mock = cls.scheduler_patch.start()

        super().setUpClass(init_login_manager=False, csrf_enabled=True)

    def setUp(self):
        super().setUp(with_test_client=False)

    def get_csrf_token(self, route):
        response = self.client.get(route)
        self.assertEqual(response.status_code, 200)
        csrf_token = b'name="csrf_token" type="hidden" value="' in response.data
        if not csrf_token:
            raise ValueError("CSRF token not found in form")
        token_start = response.data.index(b'name="csrf_token" type="hidden" value="') + len(
            b'name="csrf_token" type="hidden" value="')
        token_end = response.data.index(b'"', token_start)
        return response.data[token_start:token_end]

    def test_home_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Home', response.data)

    def test_login_page(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

    def test_register_user(self):
        csrf_token = self.get_csrf_token('/register')
        response = self.client.post('/register', data={
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'testpassword',
            'confirm_password': 'testpassword',
            'csrf_token': csrf_token
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Registration successful', response.data)

        # Check if user was actually created in the database
        user = self.session.query(User).filter_by(username='testuser').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'testuser@example.com')

        # Deleting the user from the database
        self.session.delete(user)
        self.session.commit()
        self.session.flush()

    def test_config_loading(self):
        # Test default config loading
        with self.app.app_context():
            self.assertIsInstance(self.app.config['PERMANENT_SESSION_LIFETIME'], timedelta)
            self.assertEqual(self.app.config['PERMANENT_SESSION_LIFETIME'],
                             timedelta(minutes=15))  # Assuming default is 15 minutes

        # Test custom config loading
        class CustomConfig(AppConfig):
            PERMANENT_SESSION_LIFETIME = timedelta(hours=1)

        custom_app = create_app(CustomConfig)
        with custom_app.app_context():
            self.assertEqual(custom_app.config['PERMANENT_SESSION_LIFETIME'], timedelta(hours=1))

    def test_session_timeout(self):
        with self.app.test_client() as client:
            # Set up a session
            with client.session_transaction() as sess:
                sess['last_active'] = (datetime.now() - timedelta(seconds=3601)).isoformat()

            # Make a request
            response = client.get('/')

            # Check if redirected to login page due to session timeout
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login', response.location)

    def test_session_active(self):
        with self.app.test_client() as client:
            # Set up a recent session
            with client.session_transaction() as sess:
                sess['last_active'] = datetime.now().isoformat()

            # Make a request
            response = client.get('/')

            # Check if session is still active
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Home', response.data)

    def test_security_headers(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

        # Check security headers
        self.assertIn('Strict-Transport-Security', response.headers)
        self.assertIn('X-XSS-Protection', response.headers)
        self.assertIn('X-Content-Type-Options', response.headers)
        self.assertIn('X-Frame-Options', response.headers)

        self.assertEqual(response.headers['Strict-Transport-Security'], 'max-age=31536000; includeSubDomains')
        self.assertEqual(response.headers['X-XSS-Protection'], '1; mode=block')
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['X-Frame-Options'], 'SAMEORIGIN')


if __name__ == '__main__':
    unittest.main()
