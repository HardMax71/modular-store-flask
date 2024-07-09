from flask import Flask

from .views import init_compare, add_to_comparison


def create_compare_routes(app: Flask) -> None:
    """
    Initialize comparison routes.

    :param app: Flask application instance
    """
    init_compare(app)


# Expose necessary functions
__all__ = ['create_compare_routes', 'add_to_comparison']
