from typing import Optional

from flask import Blueprint, render_template, request, Flask
from flask.typing import ResponseValue

from modular_store_backend.modules.filter.utils import filter_products, paginate_query, get_categories, \
    get_promoted_products

filter_bp = Blueprint('filter', __name__)


@filter_bp.route('/filter')
def filter_route() -> ResponseValue:
    """Filter products based on various query parameters and render the results."""
    category_id: Optional[str] = request.args.get('category_id')
    name_query: Optional[str] = request.args.get('name_query')
    sort_by: Optional[str] = request.args.get('sort_by')
    tag_query: Optional[str] = request.args.get('tag_query')
    page: int = request.args.get('page', 1, type=int)

    products_query = filter_products(category_query=category_id,
                                     name_query=name_query,
                                     sort_by=sort_by,
                                     tag_query=tag_query)
    products, in_total, total_pages, per_page = paginate_query(products_query, page)

    categories = get_categories()
    promoted_products = get_promoted_products(products_query)

    return render_template('index.html', products=products,
                           current_page=page, total_pages=total_pages, categories=categories,
                           promoted_products=promoted_products, per_page=per_page, in_total=in_total)


def init_filter(app: Flask) -> None:
    """Initialize the filter blueprint."""
    app.register_blueprint(filter_bp)
