# tests/base_test.py
import unittest

from flask_login import LoginManager

from app import create_app
from config import AppConfig
from modules.db.database import db, Base


class BaseIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls, init_login_manager: bool = True,
                   csrf_enabled: bool = False,
                   server_name: str = 'localhost'):
        AppConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        cls.app = create_app(AppConfig)
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = csrf_enabled
        cls.app.config['SERVER_NAME'] = server_name

        cls.app_context = cls.app.app_context()
        cls.app_context.push()

        cls.session = db.session
        cls.client = cls.app.test_client()

        if init_login_manager:
            LoginManager().init_app(cls.app)

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
