from flask import Flask

from .views import init_profile, profile_info


def create_profile_routes(app: Flask) -> None:
    init_profile(app)


# Expose necessary functions if needed
__all__ = ['create_profile_routes']
