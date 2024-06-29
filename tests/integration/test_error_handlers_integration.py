import unittest

from app import create_app
from config import AppConfig
from tests.base_integration_test import BaseIntegrationTest


class TestErrorHandlersIntegration(BaseIntegrationTest):
    @classmethod
    def setUpClass(cls):
        AppConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        cls.app = create_app(AppConfig)
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False

        # Add a route that deliberately raises an exception
        @cls.app.route('/trigger-error')
        def trigger_error():
            raise Exception("Deliberate 500 error")

        cls.client = cls.app.test_client()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

    def test_404_error(self):
        response = self.client.get('/nonexistent-page')
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'The server cannot find the requested page', response.data)

    def test_500_error(self):
        with self.app.test_client() as client:
            # Disable exception handling for this test
            client.application.config['TESTING'] = False
            response = client.get('/trigger-error')
            self.assertEqual(response.status_code, 500)
            self.assertIn(b'The server has encountered a situation it doesn\'t know how to handle', response.data)

    def test_error_without_user_session(self):
        response = self.client.get('/nonexistent-page')
        self.assertIn(b'Error type: 404', response.data)

    def test_error_with_user_session(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        response = self.client.get('/nonexistent-page')
        self.assertIn(b'Error type: 404', response.data)

    def test_error_includes_request_url(self):
        response = self.client.get('/nonexistent-page')
        self.assertIn(b'/nonexistent-page', response.data)


if __name__ == '__main__':
    unittest.main()
