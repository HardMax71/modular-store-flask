from datetime import datetime
from typing import Optional, List, Tuple

from sqlalchemy import or_, func, select
from sqlalchemy.orm import Query

from config import AppConfig
from modules.db.models import Goods, Category, Tag, Review, goods_tags
from modules.db.models import ProductPromotion
from modules.filter.sort_options import SortOptions


def filter_products(
        query: Optional[Query] = None,
        name_query: Optional[str] = None,
        category_query: Optional[int] = None,
        sort_by: Optional[str] = None,
        tag_query: Optional[str] = None
) -> Query:
    if query is None:
        query = Goods.query.filter(Goods.stock > 0)

    if name_query:
        query = query.filter(Goods.samplename.ilike(f'%{name_query}%'))

    if category_query:
        subcategories = select(Category.id).where(
            or_(Category.id == category_query, Category.parent_id == category_query)
        ).scalar_subquery()
        query = query.filter(Goods.category_id.in_(subcategories))

    if tag_query:
        query = query.join(goods_tags).join(Tag).filter(Tag.name.ilike(f'%{tag_query}%'))

    if sort_by:
        sort_option = SortOptions.get_by_key(sort_by)
        if sort_option:
            query = sort_option.apply(query)

    return query


def get_filter_options():
    categories = get_categories()
    tags = get_tags()
    sort_options = [{'value': option.key, 'label': option.label} for option in SortOptions.get_all()]

    filter_options = {
        'categories': categories,
        'tags': tags,
        'sort_options': sort_options,
    }
    return filter_options


def get_categories():
    categories_query = Category.query.all()
    return [{'id': category.id, 'name': category.name, 'parent_id': category.parent_id} for category in
            categories_query]


def get_tags():
    tags_query = Tag.query.all()
    return [{'id': tag.id, 'name': tag.name} for tag in tags_query]


def get_promoted_products(shirts_query: Optional[Query] = None) -> List[Goods]:
    if shirts_query is None:
        shirts_query = Goods.query.filter(Goods.stock > 0)

    current_timestamp = datetime.now()
    return shirts_query.join(ProductPromotion).filter(
        ProductPromotion.start_date <= current_timestamp,
        ProductPromotion.end_date >= current_timestamp
    ).all()


def paginate_query(query: Query, page: int) -> Tuple[List[Goods], int, int, int]:
    in_total = query.count()
    per_page = AppConfig.PER_PAGE
    offset = (page - 1) * per_page
    paginated_query = query.offset(offset).limit(per_page).all()

    total_pages = (in_total + per_page - 1) // per_page

    return paginated_query, in_total, total_pages, per_page
