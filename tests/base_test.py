# tests/base_test.py
import unittest
from dataclasses import dataclass

from flask_login import LoginManager

from app import create_app
from config import AppConfig
from modules.db.database import db, Base
from modules.db.models import User


@dataclass
class TestConfig(AppConfig):
    def __init__(self):
        super().__init__()
        self.TESTING = True
        self.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        self.WTF_CSRF_ENABLED = False
        self.SERVER_NAME = 'localhost'

    @classmethod
    def create(cls, **kwargs):
        config = cls()
        for key, value in kwargs.items():
            setattr(config, key, value)
        return config


class BaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls, init_login_manager: bool = True,
                   csrf_enabled: bool = False,
                   server_name: str = 'localhost',
                   define_load_user: bool = False):
        test_config = TestConfig.create(WTF_CSRF_ENABLED=csrf_enabled, SERVER_NAME=server_name)

        # Ensure that we are using an in-memory database for testing
        assert test_config.SQLALCHEMY_DATABASE_URI == 'sqlite:///:memory:'

        cls.app = create_app(test_config)

        cls.app_context = cls.app.app_context()
        cls.app_context.push()

        cls.session = db.session
        cls.client = cls.app.test_client()

        if init_login_manager:
            LoginManager().init_app(cls.app)

        if define_load_user:
            @cls.app.login_manager.user_loader
            def load_user(user_id):
                return db.session.get(User, user_id)

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
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
