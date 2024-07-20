from flask import Flask

from .views import init_tickets


def create_ticket_routes(app: Flask) -> None:
    """
    Initialize ticket routes.

    :param app: Flask application instance
    """
    init_tickets(app)


# Expose necessary functions
__all__ = ['create_ticket_routes']
