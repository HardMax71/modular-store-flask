# /modular_store_backend/tests/base_test.py
import unittest

from flask_login import LoginManager

from modular_store_backend.app import create_app, load_config
from modular_store_backend.modules.db.database import db, Base
from modular_store_backend.modules.db.models import User


class TestConfig:
    @staticmethod
    def create(**kwargs):
        # Load the default config
        config = load_config('./modular_store_backend/config.yaml')
        # Override with test-specific settings
        config.update({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False,
            'SERVER_NAME': 'localhost'
        })
        # Apply any additional overrides
        config.update(kwargs)
        return config


class BaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls, init_login_manager: bool = True,
                   csrf_enabled: bool = False,
                   server_name: str = 'localhost',
                   define_load_user: bool = False):
        test_config = TestConfig.create(WTF_CSRF_ENABLED=csrf_enabled, SERVER_NAME=server_name)
        # Ensure that we are using an in-memory database for testing
        assert test_config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'

        # Pass the test_config to create_app
        cls.app = create_app(config=test_config)

        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        cls.session = db.session
        cls.client = cls.app.test_client()

        if init_login_manager:
            LoginManager().init_app(cls.app)

        if define_load_user:
            @cls.app.login_manager.user_loader
            def load_user(user_id):
                return cls.session.get(User, user_id)

    @classmethod
    def tearDownClass(cls):
        cls.session.remove()
        db.engine.dispose()
        cls.app_context.pop()

    def setUp(self, with_test_client: bool = True):
        if with_test_client:
            self.client = self.app.test_client()
        self.session = db.session
        self.session.begin()

    def tearDown(self):
        self.session.remove()
        Base.metadata.drop_all(bind=db.engine)
        Base.metadata.create_all(bind=db.engine)

    # used in integration tests
    def get_flashed_messages_from_session(self):
        with self.client.session_transaction() as session:
            return session.get('_flashes', [])

    # used in unit tests
    def get_flashed_messages_from_djinja_globals(self):
        return [str(message) for message in self.app.jinja_env.globals['get_flashed_messages']()]
