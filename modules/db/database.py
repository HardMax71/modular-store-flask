from typing import Optional

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker, Session


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self) -> None:  # lazy initialization
        self._engine: Optional[Engine] = None
        self._session: Optional[scoped_session[Session]] = None
        self._app: Optional[Flask] = None
        self.metadata = Base.metadata

    def init_app(self, app: Flask) -> None:
        self._app = app
        app.teardown_appcontext(self.close)  # type: ignore

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            if self._app is None:
                raise RuntimeError("Application not initialized. Call init_app() first.")
            self._engine = create_engine(
                self._app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:'),
                echo=self._app.config.get('SQLALCHEMY_ECHO', False),
                pool_size=self._app.config.get('SQLALCHEMY_POOL_SIZE', 5),
            )
        return self._engine

    @property
    def session(self) -> scoped_session[Session]:
        if self._session is None:
            if self._app is None:
                raise RuntimeError("Application not initialized. Call init_app() first.")
            self._session = self.create_session(self.engine)
        return self._session

    def close(self, exception: Optional[Exception] = None) -> None:
        if self._session is not None:
            self._session.remove()

    def create_session(self, engine: Engine) -> scoped_session[Session]:
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return scoped_session(session_factory)

    def init_db(self) -> None:
        self.metadata.create_all(bind=self.engine)


db = Database()
