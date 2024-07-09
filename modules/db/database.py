from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import scoped_session, sessionmaker

from config import AppConfig


class Base(DeclarativeBase):
    pass


class Database:
    session: scoped_session
    engine: Engine

    def __init__(self, app: Flask = None):
        self.init_db()
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """
        Initialize the application with the database configuration.

        :param app: Flask application instance
        """
        app.before_request(self.open)
        app.teardown_appcontext(self.close)

    def open(self) -> None:
        """
        Open a new database session at the beginning of a request.
        """
        self.session = self.create_session(self.engine)

    def close(self, exception: Exception) -> None:
        """
        Close the database session at the end of a request.

        :param exception: Exception object (if any)
        """
        self.session.remove()

    def create_session(self, engine: Engine) -> scoped_session:
        """
        Create a scoped session for the given engine.

        :param engine: SQLAlchemy engine
        :return: Scoped session
        """
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return scoped_session(session_factory)

    def init_db(self) -> None:
        """
        Initialize the database by creating an engine and session.
        """
        self.engine = create_engine(AppConfig.SQLALCHEMY_DATABASE_URI)
        self.session = self.create_session(self.engine)
        Base.query = self.session.query_property()
        Base.metadata.create_all(bind=self.engine)


db = Database()
