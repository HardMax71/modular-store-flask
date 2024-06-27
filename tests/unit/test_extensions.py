import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from extensions import get_locale, login_manager, init_extensions

class TestExtensionsUnit(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['BACKUP_DIR'] = '/tmp'
        self.app.config['FACEBOOK_OAUTH_CLIENT_ID'] = 'fake_fb_id'
        self.app.config['FACEBOOK_OAUTH_CLIENT_SECRET'] = 'fake_fb_secret'
        self.app.config['GOOGLE_OAUTH_CLIENT_ID'] = 'fake_google_id'
        self.app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = 'fake_google_secret'

    @patch('extensions.current_user')
    def test_get_locale_authenticated(self, mock_current_user):
        mock_current_user.is_authenticated = True
        mock_current_user.language = 'fr'
        self.assertEqual(get_locale(), 'fr')

    @patch('extensions.current_user')
    @patch('extensions.AppConfig')
    def test_get_locale_unauthenticated(self, mock_app_config, mock_current_user):
        mock_current_user.is_authenticated = False
        mock_app_config.DEFAULT_LANG = 'en'
        self.assertEqual(get_locale(), 'en')

    @patch('extensions.db_session')
    @patch('modules.db.models.User')
    @patch('extensions.scheduler.start')
    @patch('extensions.make_facebook_blueprint')
    @patch('extensions.make_google_blueprint')
    def test_load_user(self, mock_google_bp, mock_facebook_bp, mock_scheduler_start, mock_user_model, mock_db_session):
        init_extensions(self.app)  # This will set up the user_loader

        mock_user = MagicMock()
        mock_user_model.query.get.return_value = mock_user

        user_loader = self.app.login_manager._user_callback
        result = user_loader(1)

        mock_user_model.query.get.assert_called_once_with(1)
        mock_db_session.refresh.assert_called_once_with(mock_user)
        self.assertEqual(result, mock_user)

    @patch('extensions.db_session')
    @patch('modules.db.models.User')
    @patch('extensions.scheduler.start')
    @patch('extensions.make_facebook_blueprint')
    @patch('extensions.make_google_blueprint')
    def test_load_user_not_found(self, mock_google_bp, mock_facebook_bp, mock_scheduler_start, mock_user_model, mock_db_session):
        init_extensions(self.app)  # This will set up the user_loader

        mock_user_model.query.get.return_value = None

        user_loader = self.app.login_manager._user_callback
        result = user_loader(1)

        mock_user_model.query.get.assert_called_once_with(1)
        mock_db_session.refresh.assert_not_called()
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()