import unittest

from apscheduler.schedulers import SchedulerNotRunningError
from flask import Flask

from modular_store_backend.modules.db.backup import backup_database
from modular_store_backend.modules.extensions import init_extensions, scheduler


# dont inherit from BaseIntegrationTest cause need "clean" Flask app
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

        # Check if Flask-Dance blueprints are registered
        self.assertIn('facebook', self.app.blueprints)
        self.assertIn('google', self.app.blueprints)

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

    def tearDown(self):
        try:
            scheduler.shutdown()
        except SchedulerNotRunningError:
            pass


if __name__ == '__main__':
    unittest.main()
