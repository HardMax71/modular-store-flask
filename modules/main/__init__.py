from flask import Flask
from .views import init_main


def create_main_routes(app: Flask) -> None:
    init_main(app)


# Expose necessary functions
__all__ = ['create_main_routes']
