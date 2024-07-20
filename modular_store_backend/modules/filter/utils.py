from datetime import datetime
from typing import List, Tuple, Dict, Any
from typing import Optional

from flask import current_app
from sqlalchemy import func, exists, and_, or_
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.query import Query

from modular_store_backend.modules.db.database import db
from modular_store_backend.modules.db.models import Product, Category, Tag, products_tags, ProductPromotion
from modular_store_backend.modules.filter.sort_options import SortOptions


def filter_products(
        query: Optional[Query[Product]] = None,
        name_query: Optional[str] = None,
        category_query: Optional[str] = None,
        sort_by: Optional[str] = None,
        tag_query: Optional[str] = None
) -> Query[Product]:
    """
    Filter products based on various criteria.

    :param query: Initial query to apply filters on
    :param name_query: Product name to search for
    :param category_query: Category ID to filter by
    :param sort_by: Sorting option
    :param tag_query: Tag to filter by
    :return: Filtered query
    """
    if query is None:
        query = db.session.query(Product).filter(Product.stock > 0)

    query = query.options(selectinload(Product.category), selectinload(Product.tags))

    if name_query:  # Case-insensitive search
        query = query.filter(func.lower(Product.samplename).contains(name_query.lower()))

    if category_query:  # Filter by category and its subcategories
        subcategories = select(Category.id).where(
            or_(Category.id == category_query, Category.parent_id == category_query)
        ).scalar_subquery()
        query = query.filter(Product.category_id.in_(subcategories))

    if tag_query:  # Filter by tag
        tag_subquery = exists().where(
            and_(
                products_tags.c.product_id == Product.id,
                Tag.id == products_tags.c.tag_id,
                func.lower(Tag.name).contains(tag_query.lower())
            )
        )
        query = query.filter(tag_subquery)

    if sort_by:  # Apply sorting if provided
        sort_option = SortOptions.get_by_key(sort_by)
        if sort_option:
            query = sort_option.apply(query)

    return query


def get_filter_options() -> Dict[str, Any]:
    """
    Get filter options for categories, tags, and sorting.

    :return: Dictionary containing filter options
    """
    categories = get_categories()
    tags = get_tags()
    sort_options = [{'value': option.key, 'label': option.label} for option in SortOptions.get_all()]

    filter_options = {
        'categories': categories,
        'tags': tags,
        'sort_options': sort_options,
    }
    return filter_options


def get_categories() -> List[Dict[str, Any]]:
    categories_query = db.session.query(Category).all()
    return [{'id': category.id, 'name': category.name, 'parent_id': category.parent_id} for category in
            categories_query]


def get_tags() -> List[Dict[str, Any]]:
    """
    Get a list of all tags.

    :return: List of tags with their details
    """
    tags_query = db.session.query(Tag).all()
    return [{'id': tag.id, 'name': tag.name} for tag in tags_query]


def get_promoted_products(products_query: Optional[Query[Product]] = None) -> List[Product]:
    """
    Get a list of promoted products.

    :param products_query: Initial query to apply promotions on
    :return: List of promoted products
    """
    if products_query is None:
        products_query = db.session.query(Product).filter(Product.stock > 0)

    current_timestamp = datetime.now()
    return products_query.join(ProductPromotion).filter(
        ProductPromotion.start_date <= current_timestamp,
        ProductPromotion.end_date >= current_timestamp
    ).all()


def paginate_query(query: Query[Product], page: int) -> Tuple[List[Product], int, int, int]:
    """
    Paginate a query.

    :param query: Query to paginate
    :param page: Page number
    :return: Tuple containing the paginated results, total items, total pages, and items per page
    """
    in_total = query.count()
    per_page = current_app.config['PER_PAGE']
    offset = (page - 1) * per_page
    paginated_query = query.offset(offset).limit(per_page).all()

    total_pages = (in_total + per_page - 1) // per_page

    return paginated_query, in_total, total_pages, per_page
