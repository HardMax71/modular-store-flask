from flask import Flask
from flask_limiter import Limiter
from .views import init_auth


def create_auth_routes(app: Flask, limiter: Limiter) -> None:
    init_auth(app, limiter)