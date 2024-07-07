from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base

from config import AppConfig

Base = declarative_base()


class Database:
    def __init__(self, app: Flask = None):
        self.init_db()
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        app.before_request(self.open)
        app.teardown_appcontext(self.close)

    def open(self):
        session = self.create_session(self.engine)
        self.session = session

    def close(self, exception=None):
        self.session.remove()

    def create_session(self, engine):
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return scoped_session(session_factory)

    def init_db(self) -> None:
        self.engine = create_engine(AppConfig.SQLALCHEMY_DATABASE_URI)
        self.session = self.create_session(self.engine)
        Base.query = self.session.query_property()
        Base.metadata.create_all(bind=self.engine)


db = Database()
