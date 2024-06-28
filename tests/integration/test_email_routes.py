import unittest
from unittest.mock import patch, MagicMock

from flask_login import login_user
from flask_mail import Mail

from app import create_app
from config import AppConfig
from modules.db.database import db
from modules.db.models import User
from modules.email import send_wishlist_notifications


class TestEmailRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        AppConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        cls.app = create_app(AppConfig)
        cls.app.config['TESTING'] = True
        cls.mail = Mail(cls.app)
        cls.client = cls.app.test_client()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

        @cls.app.login_manager.user_loader
        def load_user(user_id):
            return User.query.get(user_id)

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        cls.app_context.pop()

    def setUp(self):
        db.session.begin(nested=True)

    def tearDown(self):
        db.session.rollback()

        def test_send_email(self):
            with self.app.app_context():
                with patch.object(self.mail, 'send') as mock_send:
                    response = self.client.post('/send-email', data={
                        'to': 'test@example.com',
                        'subject': 'Test Subject',
                        'body': 'Test Body'
                    })
                    self.assertEqual(response.status_code, 200)
                    mock_send.assert_called_once()

        @patch('flask_login.utils._get_user')
        def test_send_wishlist_notifications(self, mock_current_user):
            with self.app.app_context():
                with patch('modules.db.models.User.get_wishlist_notifications') as mock_get_notifications:
                    with patch.object(self.mail, 'send') as mock_send:
                        mock_user = MagicMock()
                        mock_user.id = 1
                        mock_user.username = 'testuser'
                        mock_user.email = 'test@example.com'
                        mock_current_user.return_value = mock_user

                        db.session.add(mock_user)
                        db.session.commit()

                        mock_get_notifications.return_value = (['item1'], ['item2'])
                        send_wishlist_notifications()
                        self.assertTrue(mock_send.called)

        def test_send_order_confirmation_email(self):
            with self.app.app_context():
                with patch.object(self.mail, 'send') as mock_send:
                    response = self.client.post('/send-order-confirmation-email', data={
                        'email': 'test@example.com',
                        'name': 'Test User'
                    })
                    self.assertEqual(response.status_code, 200)
                    mock_send.assert_called_once()

    if __name__ == '__main__':
        unittest.main()
