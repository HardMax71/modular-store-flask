# /modular_store_backend/tests/unit/test_database.py
import unittest
from unittest.mock import patch, MagicMock

from flask import Flask
from sqlalchemy.orm import scoped_session

from modular_store_backend.modules.db.database import Database, db


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_ECHO'] = False
        self.app.config['SQLALCHEMY_POOL_SIZE'] = 5

    def test_init_app(self):
        database = Database()
        database.init_app(self.app)
        self.assertEqual(database._app, self.app)

    def test_engine_property(self):
        database = Database()
        database.init_app(self.app)
        engine = database.engine
        self.assertIsNotNone(engine)
        self.assertEqual(str(engine.url), 'sqlite:///:memory:')

    def test_session_property(self):
        database = Database()
        database.init_app(self.app)
        session = database.session
        self.assertIsInstance(session, scoped_session)

    def test_close(self):
        database = Database()
        database.init_app(self.app)
        mock_session = MagicMock()
        database._session = mock_session
        database.close()
        mock_session.remove.assert_called_once()

    @patch('modular_store_backend.modules.db.database.create_engine')
    def test_engine_creation(self, mock_create_engine):
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        database = Database()
        database.init_app(self.app)
        engine = database.engine

        mock_create_engine.assert_called_once_with(
            'sqlite:///:memory:',
            echo=False,
            pool_size=5
        )
        self.assertEqual(engine, mock_engine)

    def test_create_session(self):
        database = Database()
        database.init_app(self.app)
        engine = MagicMock()
        session = database.create_session(engine)
        self.assertIsInstance(session, scoped_session)

    @patch('modular_store_backend.modules.db.database.Base.metadata.create_all')
    def test_init_db(self, mock_create_all):
        database = Database()
        database.init_app(self.app)
        database.init_db()
        mock_create_all.assert_called_once_with(bind=database.engine)

    def test_global_db_instance(self):
        self.assertIsInstance(db, Database)


if __name__ == '__main__':
    unittest.main()
