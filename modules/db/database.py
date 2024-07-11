from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker, Session


class Base(DeclarativeBase):
    pass


class Database:
    # lazy initialization of the engine and session
    def __init__(self) -> None:
        self._engine = None
        self._session = None
        self._app = None
        self.metadata = Base.metadata

    def init_app(self, app: Flask) -> None:
        self._app = app
        app.before_request(self.open)
        app.teardown_appcontext(self.close)  # type: ignore

    @property
    def engine(self):
        if self._engine is None:
            if self._app is None:
                raise RuntimeError("Application not initialized. Call init_app() first.")
            self._engine = create_engine(self._app.config['SQLALCHEMY_DATABASE_URI'])
        return self._engine

    @property
    def session(self):
        if self._session is None:
            if self._app is None:
                raise RuntimeError("Application not initialized. Call init_app() first.")
            self._session = self.create_session(self.engine)
        return self._session

    def open(self) -> None:
        pass  # The session is now created on-demand

    def close(self, exception: Exception) -> None:
        if self._session is not None:
            self._session.remove()

    def create_session(self, engine: Engine) -> scoped_session[Session]:
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return scoped_session(session_factory)

    def init_db(self) -> None:
        Base.query = self.session.query_property()
        Base.metadata.create_all(bind=self.engine)


db = Database()
