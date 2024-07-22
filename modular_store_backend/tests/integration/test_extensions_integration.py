import unittest

from apscheduler.schedulers import SchedulerNotRunningError
from flask import Flask

from modular_store_backend.modules.db.backup import backup_database
from modular_store_backend.modules.extensions import init_extensions, scheduler
from modular_store_backend.modules.oauth_login import oauth


class TestExtensionsIntegration(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['BACKUP_DIR'] = '/tmp'
        self.app.config['FACEBOOK_OAUTH_CLIENT_ID'] = 'fake_fb_id'
        self.app.config['FACEBOOK_OAUTH_CLIENT_SECRET'] = 'fake_fb_secret'
        self.app.config['GOOGLE_OAUTH_CLIENT_ID'] = 'fake_google_id'
        self.app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = 'fake_google_secret'
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['BACKUP_INTERVAL'] = 86400

    def test_init_extensions(self):
        init_extensions(self.app)

        # Check if all extensions are initialized
        self.assertIn('babel', self.app.extensions)
        self.assertTrue(hasattr(self.app, 'login_manager'))
        self.assertIn('mail', self.app.extensions)
        self.assertIn('cache', self.app.extensions)

        # Check if scheduler job is added
        job = next((job for job in scheduler.get_jobs() if job.func == backup_database), None)
        # Check the string representation of job args
        self.assertEqual(len(job.args), 1)
        self.assertIsInstance(job.args[0], Flask)
        self.assertEqual(str(job.args[0]), str(self.app))

        # Check if OAuth is initialized
        self.assertIn('authlib.integrations.flask_client', self.app.extensions)

        # Check if OAuth clients are registered
        self.assertIn('google', oauth._registry)
        self.assertIn('facebook', oauth._registry)

    def test_babel_initialization(self):
        init_extensions(self.app)
        self.assertIn('babel', self.app.extensions)

    def test_login_manager_initialization(self):
        init_extensions(self.app)
        self.assertTrue(hasattr(self.app, 'login_manager'))

    def test_mail_initialization(self):
        init_extensions(self.app)
        self.assertIn('mail', self.app.extensions)

    def test_cache_initialization(self):
        init_extensions(self.app)
        self.assertIn('cache', self.app.extensions)

    def test_oauth_initialization(self):
        init_extensions(self.app)

        # Check if OAuth is initialized
        self.assertIn('authlib.integrations.flask_client', self.app.extensions)

        # Check if OAuth clients are registered
        self.assertIn('google', oauth._registry)
        self.assertIn('facebook', oauth._registry)

        # Check if OAuth clients have correct configuration
        google_client = oauth._registry['google']
        self.assertEqual(google_client[1]['client_id'], 'fake_google_id')
        self.assertEqual(google_client[1]['client_secret'], 'fake_google_secret')
        self.assertEqual(google_client[1]['server_metadata_url'],
                         'https://accounts.google.com/.well-known/openid-configuration')

        facebook_client = oauth._registry['facebook']
        self.assertEqual(facebook_client[1]['client_id'], 'fake_fb_id')
        self.assertEqual(facebook_client[1]['client_secret'], 'fake_fb_secret')
        self.assertEqual(facebook_client[1]['authorize_url'], 'https://www.facebook.com/dialog/oauth')

    def tearDown(self):
        try:
            scheduler.shutdown()
        except SchedulerNotRunningError:
            pass


if __name__ == '__main__':
    unittest.main()
