from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base

from config import AppConfig

Base = declarative_base()


class Database:
    def __init__(self, app: Flask = None):
        self.app = app
        if app is not None:
            self.init_app(app)
        self.init_db()

    def init_app(self, app: Flask):
        app.teardown_appcontext(self.shutdown_session)

    def create_engine(self):
        return create_engine(AppConfig.SQLALCHEMY_DATABASE_URI,
                             connect_args={"check_same_thread": False})

    def create_session(self, engine):
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return scoped_session(session_factory)

    def shutdown_session(self, exception=None):
        self.session.remove()

    def init_db(self):
        self.engine = self.create_engine()
        self.session = self.create_session(self.engine)
        Base.query = self.session.query_property()
        Base.metadata.create_all(bind=self.engine)


db = Database()
