from flask import Flask

from .views import init_admin


def create_admin(app: Flask) -> None:
    init_admin(app)
