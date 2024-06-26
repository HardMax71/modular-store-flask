from flask import Blueprint, render_template, request

from .utils import filter_products, paginate_query, get_categories, get_promoted_products

filter_bp = Blueprint('filter', __name__)


@filter_bp.route('/filter')
def filter_route():
    category_id = request.args.get('category_id')
    name_query = request.args.get('name_query')
    sort_by = request.args.get('sort_by')
    tag_query = request.args.get('tag_query')
    page = request.args.get('page', 1, type=int)

    shirts_query = filter_products(category_query=category_id,
                                   name_query=name_query,
                                   sort_by=sort_by,
                                   tag_query=tag_query)
    shirts, in_total, total_pages, per_page = paginate_query(shirts_query, page)

    categories = get_categories()
    promoted_products = get_promoted_products(shirts_query)

    return render_template('index.html', shirts=shirts,
                           current_page=page, total_pages=total_pages, categories=categories,
                           promoted_products=promoted_products, per_page=per_page, in_total=in_total)


def init_filter(app):
    app.register_blueprint(filter_bp)
