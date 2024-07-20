from flask import Flask

from modular_store_backend.modules.filter.utils import (
    filter_products,
    get_filter_options,
    get_categories,
    get_tags,
    get_promoted_products,
    paginate_query
)
from modular_store_backend.modules.filter.views import init_filter


def create_filter_routes(app: Flask) -> None:
    init_filter(app)


# Expose necessary functions
__all__ = [
    'create_filter_routes',
    'filter_products',
    'get_filter_options',
    'get_categories',
    'get_tags',
    'get_promoted_products',
    'paginate_query'
]
