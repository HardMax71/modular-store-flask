# /modular_store_backend/modules/filter/sort_options.py
from typing import Optional

from flask_babel import gettext as _
from sqlalchemy import func
from sqlalchemy.orm import Query

from modular_store_backend.modules.db.models import Product, Review


class SortOption:
    def __init__(self, key: str, label: str, field: any, order: str = 'asc') -> None:
        """
        Initialize a sort option.

        :param key: Key for the sort option
        :param label: Label for the sort option
        :param field: Field to sort by
        :param order: Sort order ('asc' or 'desc')
        """
        self.key = key
        self.label = label
        self.field = field
        self.order = order

    def apply(self, query: Query[Product]) -> Query[Product]:
        """
        Apply the sort option to the query.

        :param query: SQLAlchemy query
        :return: Modified query with sorting applied
        """
        if self.key == 'rating':
            query = query.outerjoin(Review, Review.product_id == Product.id).group_by(Product.id)
        order_func = getattr(self.field, self.order)
        return query.order_by(order_func().nullslast())


class SortOptions:
    PRICE_ASC = SortOption('price_asc', _('Price: Low to High'), Product.current_price, 'asc')
    PRICE_DESC = SortOption('price_desc', _('Price: High to Low'), Product.current_price, 'desc')
    AVG_RATING_DESC = SortOption('rating', _('Rating: High to Low'), func.coalesce(func.avg(Review.rating), 0), 'desc')

    @classmethod
    def get_all(cls) -> list[SortOption]:
        """
        Get all sort options.

        :return: list of all sort options
        """
        return [getattr(cls, attr) for attr in dir(cls) if isinstance(getattr(cls, attr), SortOption)]

    @classmethod
    def get_by_key(cls, key: str) -> Optional[SortOption]:
        """
        Get a sort option by key.

        :param key: Key of the sort option
        :return: Sort option if found, otherwise None
        """
        return next((option for option in cls.get_all() if option.key == key), None)
