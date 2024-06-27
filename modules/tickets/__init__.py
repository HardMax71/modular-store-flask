from flask import Flask

from .views import init_tickets


def create_ticket_routes(app: Flask) -> None:
    init_tickets(app)


# Expose necessary functions if needed
__all__ = ['create_ticket_routes']
