from flask import Flask

from modular_store_backend.modules.compare.views import add_to_comparison, init_compare


def create_compare_routes(app: Flask) -> None:
    """
    Initialize comparison routes.

    :param app: Flask application instance
    """
    init_compare(app)


# Expose necessary functions
__all__ = ['create_compare_routes', 'add_to_comparison']
