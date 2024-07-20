from flask import Flask

from modular_store_backend.modules.profile.views import init_profile


def create_profile_routes(app: Flask) -> None:
    init_profile(app)


# Expose necessary functions if needed
__all__ = ['create_profile_routes']
