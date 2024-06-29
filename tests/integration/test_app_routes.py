import unittest
from unittest.mock import patch

from modules.db.database import db
from modules.db.models import User
from tests.base_integration_test import BaseIntegrationTest


class TestAppRoutes(BaseIntegrationTest):
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
        user = User.query.filter_by(username='testuser').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'testuser@example.com')

        # Deleting the user from the database
        db.session.delete(user)
        db.session.commit()
        db.session.flush()


if __name__ == '__main__':
    unittest.main()
