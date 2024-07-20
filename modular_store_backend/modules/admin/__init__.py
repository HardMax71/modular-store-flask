from flask import Flask

from modular_store_backend.modules.admin.views import init_admin


def create_admin(app: Flask) -> None:
    init_admin(app)
