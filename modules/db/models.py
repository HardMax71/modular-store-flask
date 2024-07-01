import os
from datetime import datetime, date
from typing import Tuple, List, Optional

from flask_login import current_user, UserMixin
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, Date, ForeignKey, CheckConstraint, \
    Table, DateTime, UniqueConstraint
from sqlalchemy import case
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, backref, joinedload
from sqlalchemy.sql import func

from modules.db.database import Base, db


class User(Base, UserMixin):
    """
    Represents a user in the system.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(Text, nullable=False, unique=True, index=True)
    password = Column(Text, nullable=False)
    fname = Column(Text)
    lname = Column(Text)
    email = Column(Text, unique=True, index=True)
    phone = Column(Text)
    _profile_picture = Column(Text, default='user-icon.png')
    language = Column(String(5), default='en')
    notifications_enabled = Column(Boolean, default=True)
    email_notifications_enabled = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    addresses = relationship('Address', backref='user', lazy='select')
    cart_items = relationship('Cart', backref='user', lazy='select')
    purchases = relationship('Purchase', backref='user', lazy='select')
    reviews = relationship('Review', backref='user', lazy='select')
    wishlist_items = relationship('Wishlist', backref='user',
                                  lazy='dynamic')  # Consider using dynamic for collections that could be large
    notifications = relationship('Notification', backref='user', lazy='select')
    social_accounts = relationship('SocialAccount', back_populates='user', lazy='select')

    recently_viewed_products = relationship('RecentlyViewedProduct', backref='user', lazy='select')
    preferences = relationship('UserPreference', backref='user', lazy='select')

    @property
    def profile_picture(self):
        if self._profile_picture is None:
            return 'user-icon.png'

        image_path = os.path.join('static', 'img', 'profile_pictures', self._profile_picture)

        if not os.path.exists(image_path) or not os.path.isfile(image_path):
            return 'user-icon.png'

        return self._profile_picture

    @profile_picture.setter
    def profile_picture(self, value):
        self._profile_picture = value

    def __str__(self):
        return self.username

    @staticmethod
    def get_wishlist_notifications() -> Tuple[List['Goods'], List['Goods']]:
        """
        Get the user's wishlist notifications for items on sale and back in stock.
        """

        wishlist_items = db.session.query(Wishlist).options(joinedload(Wishlist.goods)).filter_by(
            user_id=current_user.id).all()  # Eager loading

        on_sale_items = []
        back_in_stock_items = []

        for item in wishlist_items:
            goods = item.goods

            if goods.onSale:
                on_sale_items.append(goods)
            elif goods.stock > 0:
                back_in_stock_items.append(goods)

        return on_sale_items, back_in_stock_items


class RecentlyViewedProduct(Base):
    __tablename__ = 'recently_viewed_products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    goods_id = Column(Integer, ForeignKey('goods.id'), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    goods = relationship('Goods', backref='recently_viewed_by', lazy='select')

    def __str__(self):
        return f'RecentlyViewedProduct {self.id}'


class UserPreference(Base):
    __tablename__ = 'user_preferences'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False, index=True)
    interest_level = Column(Integer, nullable=False)

    category = relationship('Category', backref='user_preferences', lazy='select')

    def __str__(self):
        return f'UserPreference {self.id} {self.interest_level}'


class Cart(Base):
    __tablename__ = 'cart'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    goods_id = Column(Integer, ForeignKey('goods.id'), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    variant_options = Column(Text)

    goods = relationship('Goods', backref='cart_items', lazy='joined')

    def __str__(self):
        return f'Cart {self.id}'

    @staticmethod
    def update_stock(goods_id: int, quantity: int) -> None:
        """
        Update the stock of a goods item after a purchase.
        """

        goods = db.session.query(Goods).get(goods_id)
        if goods:
            goods.stock -= quantity
            db.session.commit()

    @staticmethod
    def total_quantity() -> int:
        """
        Get the total quantity of items in the user's cart.
        """
        if not current_user or not current_user.is_authenticated:
            return 0

        result = db.session.query(func.coalesce(func.sum(Cart.quantity), 0)) \
            .filter(Cart.user_id == current_user.id) \
            .scalar()

        return int(result)

    @staticmethod
    def subtotal() -> float:
        """
        Calculate the subtotal of all items in the user's cart.
        """
        if not current_user.is_authenticated:
            return 0.0

        result = db.session.query(func.coalesce(func.sum(Cart.price * Cart.quantity), 0.0)) \
            .filter(Cart.user_id == current_user.id) \
            .scalar()

        return float(result)

    @staticmethod
    def cart_info() -> Tuple[int, float, float]:
        """
        Calculate the total items, total amount after discount, and maximum discount percentage
        available to the current user.

        Returns:
            tuple: A tuple containing:
                - total_items (int): The total number of items in the user's cart.
                - total_amount (float): The total amount after applying the maximum discount.
                - max_discount (float): The maximum discount percentage available to the user.
        """
        if not current_user or not current_user.is_authenticated:
            return 0, 0.0, 0.0

        cart_items = db.session.query(
            func.sum(Cart.quantity).label('total_items'),
            func.sum(Cart.quantity * Cart.price).label('subtotal')
        ).filter_by(user_id=current_user.id).first()

        total_items: int = int(cart_items.total_items or 0)
        subtotal: float = float(cart_items.subtotal or 0.0)

        current_date: date = datetime.now().date()
        max_discount: float = db.session.query(func.max(Discount.percentage)).join(UserDiscount).filter(
            UserDiscount.user_id == current_user.id,
            Discount.start_date <= current_date,
            Discount.end_date >= current_date
        ).scalar() or 0.0

        discount_amount = subtotal * (max_discount / 100)
        total_amount = subtotal - discount_amount

        current_user.discount = max_discount

        return total_items, total_amount, max_discount


related_products = Table('related_products', Base.metadata,
                         Column('goods_id1', Integer, ForeignKey('goods.id', ondelete='CASCADE'),
                                primary_key=True),
                         Column('goods_id2', Integer, ForeignKey('goods.id', ondelete='CASCADE'),
                                primary_key=True)
                         )


class Goods(Base):
    __tablename__ = 'goods'

    id = Column(Integer, primary_key=True, autoincrement=True)
    samplename = Column(Text)
    _image = Column(Text, default='goods-icon.png')
    price = Column(Float)
    onSale = Column(Integer)
    onSalePrice = Column(Float)
    kind = Column(Text)
    goods_type = Column(Text)
    description = Column(Text)
    category_id = Column(Integer, ForeignKey('categories.id'), index=True)
    stock = Column(Integer, nullable=False, default=0)

    category = relationship('Category', backref='goods', lazy='select')
    purchase_items = relationship('PurchaseItem', lazy='select', passive_deletes=True)
    reviews = relationship('Review', backref='goods', lazy='select', passive_deletes=True)
    wishlist_items = relationship('Wishlist', backref='goods', lazy='select', passive_deletes=True)
    variants = relationship('Variant', backref='goods', lazy='select', passive_deletes=True)
    tags = relationship('Tag', secondary='goods_tags', backref='goods', lazy='select', passive_deletes=True)
    related_products = relationship('Goods', secondary='related_products',
                                    primaryjoin=(id == related_products.c.goods_id1),
                                    secondaryjoin=(id == related_products.c.goods_id2),
                                    backref=backref('related_to', lazy='select'),
                                    lazy='select',
                                    passive_deletes=True)

    @property
    def image(self):
        if self._image is None:
            return 'goods-icon.png'

        image_path = os.path.join('static', 'img', 'goods_pictures', self._image)
        if not os.path.exists(image_path) or not os.path.isfile(image_path):
            return 'goods-icon.png'

        return self._image

    @image.setter
    def image(self, value):
        self._image = value

    def __str__(self):
        sample_description = (self.description[:20] + '..') if self.description else 'No description'
        return f'{self.samplename}: {sample_description}'

    @hybrid_property
    def avg_rating(self) -> Optional[float]:
        if self.reviews:
            return db.session.query(func.avg(Review.rating)).filter_by(goods_id=self.id).scalar() or 0
        return 0

    @avg_rating.expression
    def avg_rating(cls):
        return func.coalesce(
            db.session.query(func.avg(Review.rating))
            .filter(Review.goods_id == cls.id)
            .correlate(cls)
            .scalar_subquery(),
            0
        )

    @hybrid_property
    def current_price(self):
        return self.onSalePrice if self.onSale else self.price

    @current_price.expression
    def current_price(cls):
        return case(
            (cls.onSale == 1, cls.onSalePrice),
            else_=cls.price
        )


class SocialAccount(Base):
    __tablename__ = 'social_accounts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    social_id = Column(String(255), nullable=False)
    access_token = Column(String(255), nullable=False)

    user = relationship('User', back_populates='social_accounts')

    def __str__(self):
        return self.social_id


class ComparisonHistory(Base):
    __tablename__ = 'comparison_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    product_ids = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', backref='comparison_history', lazy='joined')

    def __str__(self):
        return f'ComparisonHistory {self.id} {self.timestamp} {self.product_ids}'


class Purchase(Base):
    __tablename__ = 'purchases'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    date = Column(Date, nullable=False, default=func.current_date())
    total_price = Column(Float, nullable=False)
    discount_amount = Column(Float, nullable=False, default=0)
    delivery_fee = Column(Float, nullable=False, default=0)
    status = Column(Text)
    tracking_number = Column(Text)
    shipping_method = Column(Text)
    payment_method = Column(Text)
    payment_id = Column(Text)

    items = relationship('PurchaseItem', lazy='joined')
    shipping_address = relationship('ShippingAddress', uselist=False)

    @staticmethod
    def update_stock(purchase: 'Purchase') -> None:
        """
        Update the stock of goods items after a purchase.
        """

        for item in purchase.items:
            goods = db.session.get(Goods, item.goods_id)
            if goods:
                goods.stock -= item.quantity
        db.session.commit()


class ShippingMethod(Base):
    __tablename__ = 'shipping_methods'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    price = Column(Float, nullable=False)


class PurchaseItem(Base):
    __tablename__ = 'purchase_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    purchase_id = Column(Integer, ForeignKey('purchases.id'), nullable=False, index=True)
    goods_id = Column(Integer, ForeignKey('goods.id'), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    @property
    def goods(self) -> Goods:
        """
        Get the goods item associated with the purchase item.
        """
        return db.session.get(Goods, self.goods_id)


class ReportedReview(Base):
    __tablename__ = "reported_reviews"

    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    explanation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    review = relationship("Review", backref="reported_reviews")
    user = relationship("User", backref="reported_reviews")

    def __str__(self):
        return f'ReportedReview {self.id}'


class Review(Base):
    __tablename__ = 'reviews'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    goods_id = Column(Integer, ForeignKey('goods.id'), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    review = Column(Text)
    title = Column(Text)
    pros = Column(Text)
    cons = Column(Text)
    images = Column(Text)
    date = Column(Date, nullable=False, default=func.current_date())
    moderated = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5'),
    )

    def __str__(self):
        return f'{self.review}..'


class Address(Base):
    __tablename__ = 'addresses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    address_line1 = Column(Text, nullable=False)
    address_line2 = Column(Text)
    city = Column(Text, nullable=False)
    state = Column(Text, nullable=False)
    zip_code = Column(Text, nullable=False)
    country = Column(Text, nullable=False)

    def __str__(self):
        return f'{self.address_line1}'


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    parent_id = Column(Integer, ForeignKey('categories.id'), index=True)

    parent = relationship('Category', remote_side=[id], backref='subcategories', lazy='joined')

    def __str__(self):
        return self.name


class ShippingAddress(Base):
    __tablename__ = 'shipping_addresses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    purchase_id = Column(Integer, ForeignKey('purchases.id'), nullable=False)
    address_line1 = Column(Text, nullable=False)
    address_line2 = Column(Text)
    city = Column(Text, nullable=False)
    state = Column(Text, nullable=False)
    zip_code = Column(Text, nullable=False)
    country = Column(Text, nullable=False)

    def __repr__(self):
        return f'ShippingAddress {self.id}: {self.address_line1}>'


class Wishlist(Base):
    __tablename__ = 'wishlists'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    goods_id = Column(Integer, ForeignKey('goods.id'), nullable=False)
    variant_options = Column(Text)

    def __str__(self):
        return f'Wishlist {self.id}'


class Variant(Base):
    __tablename__ = 'variants'

    id = Column(Integer, primary_key=True, autoincrement=True)
    goods_id = Column(Integer, ForeignKey('goods.id'), nullable=False)
    name = Column(Text, nullable=False)
    value = Column(Text, nullable=False)

    def __str__(self):
        return f'{self.name}: {self.value}'


class Discount(Base):
    __tablename__ = 'discounts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(Text, nullable=False)
    percentage = Column(Float, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    def __str__(self):
        return f'{self.code}: {self.percentage}%'


class UserDiscount(Base):
    __tablename__ = 'user_discounts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    discount_id = Column(Integer, ForeignKey('discounts.id'), nullable=False)

    discount = relationship('Discount', backref='users', lazy='joined')
    user = relationship('User', backref='discounts', lazy='joined')

    __table_args__ = (
        UniqueConstraint('user_id', 'discount_id', name='unique_user_discount'),
    )


class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    message = Column(Text, nullable=False)
    read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=func.current_timestamp())

    def __str__(self):
        return f'{self.message[:20]}..'


class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)

    def __str__(self):
        return self.name


goods_tags = Table('goods_tags', Base.metadata,
                   Column('goods_id', Integer, ForeignKey('goods.id', ondelete='CASCADE'),
                          primary_key=True),
                   Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
                   )


class RequestLog(Base):
    __tablename__ = 'request_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    ip_address = Column(String(50), nullable=False)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    execution_time = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', backref='request_logs', lazy='joined')


class ProductPromotion(Base):
    __tablename__ = 'product_promotions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    goods_id = Column(Integer, ForeignKey('goods.id'), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    description = Column(Text, nullable=False)

    goods = relationship('Goods', backref='promotions', lazy='joined')

    def __str__(self):
        return f'{self.description[:20]}..'


class Ticket(Base):
    __tablename__ = 'tickets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    admin_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default='open')
    priority = Column(String(50), nullable=False, default='normal')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    user = relationship('User', backref='tickets', foreign_keys=[user_id])
    admin = relationship('User', backref='assigned_tickets', foreign_keys=[admin_id])

    def __str__(self):
        return f'Ticket {self.id}: {self.title}'


class TicketMessage(Base):
    __tablename__ = 'ticket_messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    message = Column(Text, nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship('Ticket', backref='messages')
    user = relationship('User', backref='ticket_messages')

    def __str__(self):
        return f'TicketMessage {self.id}: {self.message[:20]}...'
