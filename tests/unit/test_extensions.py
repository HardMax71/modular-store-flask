import unittest
from unittest.mock import patch

from app import create_app
from config import AppConfig
from modules.db.database import db
from modules.db.models import User
from modules.extensions.utils import get_locale, load_user


class TestExtensionsUnit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scheduler_patch = patch('modules.extensions.scheduler.start')
        cls.scheduler_mock = cls.scheduler_patch.start()

        AppConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

        cls.app = create_app(AppConfig)
        cls.client = cls.app.test_client()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

    @classmethod
    def tearDownClass(cls):
        cls.scheduler_patch.stop()
        db.session.remove()
        cls.app_context.pop()

    def setUp(self):
        db.session.begin(nested=True)

    def tearDown(self):
        db.session.rollback()

    @patch('modules.extensions.utils.current_user')
    def test_get_locale_authenticated(self, mock_current_user):
        mock_current_user.is_authenticated = True
        mock_current_user.language = 'fr'
        self.assertEqual(get_locale(), 'fr')

    @patch('modules.extensions.utils.current_user')
    def test_get_locale_unauthenticated(self, mock_current_user):
        mock_current_user.is_authenticated = False
        self.assertEqual(get_locale(), AppConfig.DEFAULT_LANG)

    def test_load_user(self):
        user = User(username='test_user', email='test@example.com', password='password')
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
