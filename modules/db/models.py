import os
from datetime import datetime, date
from typing import List, Optional
from typing import Tuple

from flask_login import current_user, UserMixin
from sqlalchemy import ForeignKey, Table, Column, CheckConstraint, UniqueConstraint
from sqlalchemy import String, Text, Integer, Boolean, DateTime, Date, Float
from sqlalchemy import func, case
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm import backref, joinedload

from config import AppConfig
from modules.db.database import Base, db


class User(Base, UserMixin):
    """
    Represents a user in the system.
    """
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(Text, nullable=False)
    fname: Mapped[Optional[str]] = mapped_column(Text)
    lname: Mapped[Optional[str]] = mapped_column(Text)
    email: Mapped[Optional[str]] = mapped_column(Text, unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(Text)
    _profile_picture: Mapped[str] = mapped_column(Text, default='user-icon.png')
    language: Mapped[str] = mapped_column(String(5), default='en')
    stripe_customer_id: Mapped[str] = mapped_column(Text, default='nonexistent_stripe_customer_id')
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    addresses: Mapped[List["Address"]] = relationship('Address', backref='user', lazy='select')
    cart_items: Mapped[List["Cart"]] = relationship('Cart', backref='user', lazy='select')
    purchases: Mapped[List["Purchase"]] = relationship('Purchase', backref='user', lazy='select')
    reviews: Mapped[List["Review"]] = relationship('Review', backref='user', lazy='select')
    wishlist_items: Mapped[List["Wishlist"]] = relationship('Wishlist', backref='user',
                                                            lazy='dynamic')  # Consider using dynamic for collections that could be large
    notifications: Mapped[List["Notification"]] = relationship('Notification', backref='user', lazy='select')
    social_accounts: Mapped[List["SocialAccount"]] = relationship('SocialAccount', back_populates='user', lazy='select')

    recently_viewed_products: Mapped[List["RecentlyViewedProduct"]] = relationship('RecentlyViewedProduct',
                                                                                   backref='user', lazy='select')
    preferences: Mapped[List["UserPreference"]] = relationship('UserPreference', backref='user', lazy='select')

    @hybrid_property
    def profile_picture(self) -> str:
        if self._profile_picture is None:
            return 'user-icon.png'

        image_path = os.path.join(AppConfig.PROFILE_PICS_FOLDER, str(self._profile_picture))

        if not os.path.exists(image_path) or not os.path.isfile(image_path):
            return 'user-icon.png'

        return str(self._profile_picture)

    @profile_picture.setter
    def profile_picture(self, value: str) -> None:
        self._profile_picture = value

    def __str__(self):  # type: ignore
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    goods_id: Mapped[int] = mapped_column(Integer, ForeignKey('goods.id'), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    goods: Mapped["Goods"] = relationship('Goods', backref='recently_viewed_by', lazy='select')

    def __str__(self):  # type: ignore
        return f'RecentlyViewedProduct {self.id}'


class UserPreference(Base):
    __tablename__ = 'user_preferences'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey('categories.id'), nullable=False, index=True)
    interest_level: Mapped[int] = mapped_column(Integer, nullable=False)

    category: Mapped["Category"] = relationship('Category', backref='user_preferences', lazy='select')

    def __str__(self):  # type: ignore
        return f'UserPreference {self.id} {self.interest_level}'


class Cart(Base):
    __tablename__ = 'cart'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    goods_id: Mapped[int] = mapped_column(Integer, ForeignKey('goods.id'), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)  # Price in cents
    variant_options: Mapped[Optional[str]] = mapped_column(Text)

    goods: Mapped["Goods"] = relationship('Goods', backref='cart_items', lazy='joined')

    def __str__(self):  # type: ignore
        return f'Cart {self.id}'

    @staticmethod
    def update_stock(goods_id: int, quantity: int) -> None:
        """
        Update the stock of a goods item after a purchase.
        """

        goods: Optional[Goods] = db.session.get(Goods, goods_id)
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
    def subtotal() -> int:
        """
        Calculate the subtotal of all items in the user's cart.
        """
        if not current_user.is_authenticated:
            return 0

        result: int = db.session.query(func.coalesce(func.sum(Cart.price * Cart.quantity), 0)) \
            .filter(Cart.user_id == current_user.id) \
            .scalar()

        return result

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

        discount_amount = subtotal * (max_discount / 100.0)
        total_amount = subtotal - discount_amount

        current_user.discount = max_discount

        return total_items, total_amount, max_discount


related_products = Table(
    'related_products',
    Base.metadata,
    Column('goods_id1', Integer, ForeignKey('goods.id', ondelete='CASCADE'), primary_key=True),
    Column('goods_id2', Integer, ForeignKey('goods.id', ondelete='CASCADE'), primary_key=True)
)


class Goods(Base):
    __tablename__ = 'goods'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    samplename: Mapped[Optional[str]] = mapped_column(Text)
    _image: Mapped[str] = mapped_column(Text, default='goods-icon.png')
    price: Mapped[Optional[int]] = mapped_column(Integer)  # Price in cents
    onSale: Mapped[Optional[int]] = mapped_column(Integer)
    onSalePrice: Mapped[Optional[int]] = mapped_column(Integer)  # Price in cents
    kind: Mapped[Optional[str]] = mapped_column(Text)
    goods_type: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('categories.id'), index=True)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    category: Mapped["Category"] = relationship('Category', backref='goods', lazy='select')
    purchase_items: Mapped[List["PurchaseItem"]] = relationship('PurchaseItem', lazy='select', passive_deletes=True)
    reviews: Mapped[List["Review"]] = relationship('Review', backref='goods', lazy='select', passive_deletes=True)
    wishlist_items: Mapped[List["Wishlist"]] = relationship('Wishlist', lazy='select',
                                                            passive_deletes=True)
    variants: Mapped[List["Variant"]] = relationship('Variant', backref='goods', lazy='select', passive_deletes=True)
    tags: Mapped[List["Tag"]] = relationship('Tag', secondary='goods_tags', backref='goods', lazy='select',
                                             passive_deletes=True)
    related_products: Mapped[List["Goods"]] = relationship(
        'Goods', secondary='related_products',
        primaryjoin=(id == related_products.c.goods_id1),
        secondaryjoin=(id == related_products.c.goods_id2),
        backref=backref('related_to', lazy='select'),
        lazy='select',
        passive_deletes=True
    )

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

    def __str__(self):  # type: ignore
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    social_id: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped["User"] = relationship('User', back_populates='social_accounts')

    def __str__(self):  # type: ignore
        return self.social_id


class ComparisonHistory(Base):
    __tablename__ = 'comparison_history'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'),
                                         nullable=False, index=True)
    product_ids: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship('User', backref='comparison_history', lazy='joined')

    def __str__(self):  # type: ignore
        return f'ComparisonHistory {self.id} {self.timestamp} {self.product_ids}'


class Purchase(Base):
    __tablename__ = 'purchases'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    total_price: Mapped[int] = mapped_column(Integer, nullable=False)  # Total price in cents
    discount_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # Discount amount in cents
    delivery_fee: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # Delivery fee in cents
    status: Mapped[Optional[str]] = mapped_column(Text)
    tracking_number: Mapped[Optional[str]] = mapped_column(Text)
    shipping_method: Mapped[Optional[str]] = mapped_column(Text)
    payment_method: Mapped[Optional[str]] = mapped_column(Text)
    payment_id: Mapped[Optional[str]] = mapped_column(Text)

    items: Mapped[List["PurchaseItem"]] = relationship('PurchaseItem', lazy='joined')
    shipping_address: Mapped[Optional["ShippingAddress"]] = relationship('ShippingAddress', uselist=False)

    @hybrid_property
    def items_subtotal(self) -> int:
        """Calculate the subtotal of all items in the purchase."""
        return sum(item.quantity * item.price for item in self.items)

    @items_subtotal.expression
    def items_subtotal(cls):
        """SQL expression for calculating the subtotal."""
        return (
            db.select(func.sum(PurchaseItem.quantity * PurchaseItem.price))
            .where(PurchaseItem.purchase_id == cls.id)
            .scalar_subquery()
        )

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)  # Price in cents


class PurchaseItem(Base):
    __tablename__ = 'purchase_items'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purchase_id: Mapped[int] = mapped_column(Integer, ForeignKey('purchases.id'), nullable=False, index=True)
    goods_id: Mapped[int] = mapped_column(Integer, ForeignKey('goods.id'), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)  # Price in cents

    purchase: Mapped["Purchase"] = relationship("Purchase", back_populates="items")
    goods: Mapped["Goods"] = relationship("Goods", back_populates="purchase_items", lazy="joined")

    def __str__(self):  # type: ignore
        return f'PurchaseItem {self.id}: {self.quantity} x {self.goods.samplename if self.goods else "Unknown"}'


class ReportedReview(Base):
    __tablename__ = "reported_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(Integer, ForeignKey("reviews.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    review: Mapped["Review"] = relationship("Review", backref="reported_reviews")
    user: Mapped["User"] = relationship("User", backref="reported_reviews")

    def __str__(self):  # type: ignore
        return f'ReportedReview {self.id}'


class Review(Base):
    __tablename__ = 'reviews'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    goods_id: Mapped[int] = mapped_column(Integer, ForeignKey('goods.id'), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review: Mapped[Optional[str]] = mapped_column(Text)
    title: Mapped[Optional[str]] = mapped_column(Text)
    pros: Mapped[Optional[str]] = mapped_column(Text)
    cons: Mapped[Optional[str]] = mapped_column(Text)
    date: Mapped[datetime] = mapped_column(Date, nullable=False, default=func.current_date())
    moderated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    images: Mapped[List["ReviewImage"]] = relationship("ReviewImage", back_populates="review",
                                                       cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5'),
    )

    def __str__(self):  # type: ignore
        return f'Review {self.id}: {self.title}'


class ReviewImage(Base):
    __tablename__ = 'review_images'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(Integer, ForeignKey('reviews.id'), nullable=False, index=True)
    _image: Mapped[str] = mapped_column('image', Text, nullable=False)

    review: Mapped["Review"] = relationship("Review", back_populates="images")
    DEFAULT_IMAGE: str = 'review_image.png'

    @hybrid_property
    def uploaded_image(self) -> str:
        if self._image is None:
            return self.DEFAULT_IMAGE

        image_path = os.path.join(AppConfig.REVIEW_PICS_FOLDER, self._image)

        if not os.path.exists(image_path) or not os.path.isfile(image_path):
            return self.DEFAULT_IMAGE

        return str(self._image)

    def __str__(self):  # type: ignore
        return f'ReviewImage {self.id} for Review {self.review_id}'


class Address(Base):
    __tablename__ = 'addresses'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    address_line1: Mapped[str] = mapped_column(Text, nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    zip_code: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(Text, nullable=False)

    def __str__(self):  # type: ignore
        return f'{self.address_line1}'


class Category(Base):
    __tablename__ = 'categories'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('categories.id'), index=True)

    parent: Mapped[Optional["Category"]] = relationship('Category', remote_side=[id], backref='subcategories',
                                                        lazy='joined')

    def __str__(self):  # type: ignore
        return self.name


class ShippingAddress(Base):
    __tablename__ = 'shipping_addresses'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purchase_id: Mapped[int] = mapped_column(Integer, ForeignKey('purchases.id'), nullable=False)
    address_line1: Mapped[str] = mapped_column(Text, nullable=False)
    address_line2: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    zip_code: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self):
        return f'ShippingAddress {self.id}: {self.address_line1}>'


class Wishlist(Base):
    __tablename__ = 'wishlists'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    goods_id: Mapped[int] = mapped_column(Integer, ForeignKey('goods.id'), nullable=False)
    variant_options: Mapped[Optional[str]] = mapped_column(Text)

    goods: Mapped["Goods"] = relationship("Goods", back_populates="wishlist_items")

    def __str__(self):  # type: ignore
        return f'Wishlist {self.id}'


class Variant(Base):
    __tablename__ = 'variants'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    goods_id: Mapped[int] = mapped_column(Integer, ForeignKey('goods.id'), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    def __str__(self):  # type: ignore
        return f'{self.name}: {self.value}'


class Discount(Base):
    __tablename__ = 'discounts'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    percentage: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[Date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Date] = mapped_column(Date, nullable=False)

    def __str__(self):  # type: ignore
        return f'{self.code}: {self.percentage}%'


class UserDiscount(Base):
    __tablename__ = 'user_discounts'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    discount_id: Mapped[int] = mapped_column(Integer, ForeignKey('discounts.id'), nullable=False)

    discount: Mapped["Discount"] = relationship('Discount', backref='users', lazy='joined')
    user: Mapped["User"] = relationship('User', backref='discounts', lazy='joined')

    __table_args__ = (
        UniqueConstraint('user_id', 'discount_id', name='unique_user_discount'),
    )


class Notification(Base):
    __tablename__ = 'notifications'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.current_timestamp())

    def __str__(self):  # type: ignore
        return f'{self.message[:20]}..' if len(self.message) > 22 else self.message


class Tag(Base):
    __tablename__ = 'tags'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)

    def __str__(self):  # type: ignore
        return self.name


goods_tags = Table(
    'goods_tags', Base.metadata,
    Column('goods_id', Integer, ForeignKey('goods.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)


class RequestLog(Base):
    __tablename__ = 'request_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    ip_address: Mapped[str] = mapped_column(String(50), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    execution_time: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[Optional["User"]] = relationship('User', backref='request_logs', lazy='joined')


class ProductPromotion(Base):
    __tablename__ = 'product_promotions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    goods_id: Mapped[int] = mapped_column(Integer, ForeignKey('goods.id'), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    goods: Mapped["Goods"] = relationship('Goods', backref='promotions', lazy='joined')

    def __str__(self):  # type: ignore
        return f'{self.description[:20]}..' if len(self.description) > 22 else self.description


class Ticket(Base):
    __tablename__ = 'tickets'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    admin_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default='open')
    priority: Mapped[str] = mapped_column(String(50), nullable=False, default='normal')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship('User', backref='tickets', foreign_keys=[user_id])
    admin: Mapped[Optional["User"]] = relationship('User', backref='assigned_tickets', foreign_keys=[admin_id])

    def __str__(self):  # type: ignore
        return f'Ticket {self.id}: {self.title}'


class TicketMessage(Base):
    __tablename__ = 'ticket_messages'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey('tickets.id'), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ticket: Mapped["Ticket"] = relationship('Ticket', backref='messages')
    user: Mapped["User"] = relationship('User', backref='ticket_messages')

    def __str__(self):  # type: ignore
        return f'TicketMessage {self.id}: {self.message[:20] if len(self.message) > 22 else self.message}...'
