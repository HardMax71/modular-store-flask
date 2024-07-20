from flask import Flask

from modular_store_backend.modules.main.views import init_main


def create_main_routes(app: Flask) -> None:
    init_main(app)


# Expose necessary functions
__all__ = ['create_main_routes']
