from sqlalchemy import func
from flask_babel import gettext as _
from modules.db.models import Goods, Review


class SortOption:
    def __init__(self, key, label, field, order='asc'):
        self.key = key
        self.label = label
        self.field = field
        self.order = order

    def apply(self, query):
        if self.key == 'rating':
            query = query.outerjoin(Review, Review.goods_id == Goods.id).group_by(Goods.id)
        order_func = getattr(self.field, self.order)
        return query.order_by(order_func().nullslast())


class SortOptions:
    PRICE_ASC = SortOption('price_asc', _('Price: Low to High'), Goods.current_price, 'asc')
    PRICE_DESC = SortOption('price_desc', _('Price: High to Low'), Goods.current_price, 'desc')
    AVG_RATING_DESC = SortOption('rating', _('Rating: High to Low'), func.coalesce(func.avg(Review.rating), 0), 'desc')

    @classmethod
    def get_all(cls):
        return [getattr(cls, attr) for attr in dir(cls) if isinstance(getattr(cls, attr), SortOption)]

    @classmethod
    def get_by_key(cls, key):
        return next((option for option in cls.get_all() if option.key == key), None)
