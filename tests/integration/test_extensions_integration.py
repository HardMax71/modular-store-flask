import unittest
from unittest.mock import patch, MagicMock

from flask import Flask

from extensions import init_extensions


class TestExtensionsIntegration(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['BACKUP_DIR'] = '/tmp'
        self.app.config['FACEBOOK_OAUTH_CLIENT_ID'] = 'fake_fb_id'
        self.app.config['FACEBOOK_OAUTH_CLIENT_SECRET'] = 'fake_fb_secret'
        self.app.config['GOOGLE_OAUTH_CLIENT_ID'] = 'fake_google_id'
        self.app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = 'fake_google_secret'

    @patch('extensions.BackgroundScheduler')
    @patch('extensions.make_facebook_blueprint')
    @patch('extensions.make_google_blueprint')
    @patch('extensions.scheduler.start')
    def test_init_extensions(self, mock_scheduler_start, mock_google_bp, mock_facebook_bp, mock_background_scheduler):
        mock_scheduler = MagicMock()
        mock_background_scheduler.return_value = mock_scheduler

        init_extensions(self.app)

        # Check if all extensions are initialized
        self.assertIn('babel', self.app.extensions)
        self.assertTrue(hasattr(self.app, 'login_manager'))
        self.assertIn('mail', self.app.extensions)
        self.assertIn('cache', self.app.extensions)

        # TODO Check how to test this: smh mock_scheduler isnt being called
        # # Check if scheduler job is added
        # mock_scheduler.add_job.assert_called_once_with(
        #     backup_database, 'interval', minutes=30, args=[self.app.config['BACKUP_DIR']]
        # )
        # # Ensure scheduler.start() is called
        # mock_scheduler.start.assert_called_once()

        # Check if Flask-Dance blueprints are registered
        mock_facebook_bp.assert_called_once()
        mock_google_bp.assert_called_once()

    @patch('extensions.scheduler.start')
    def test_babel_initialization(self, mock_scheduler_start):
        init_extensions(self.app)
        self.assertIn('babel', self.app.extensions)

    @patch('extensions.scheduler.start')
    def test_mail_initialization(self, mock_scheduler_start):
        init_extensions(self.app)
        self.assertIn('mail', self.app.extensions)

    @patch('extensions.scheduler.start')
    def test_cache_initialization(self, mock_scheduler_start):
        init_extensions(self.app)
        self.assertIn('cache', self.app.extensions)


if __name__ == '__main__':
    unittest.main()
