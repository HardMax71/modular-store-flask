from datetime import datetime
from typing import List

from sqlalchemy import desc

from modules.db.database import db
from modules.db.models import RecentlyViewedProduct, Product, UserPreference


def update_recently_viewed_products(user_id: int, product_id: int) -> None:
    """Update or create a recently viewed product entry."""
    db.session.merge(RecentlyViewedProduct(
        user_id=user_id,
        product_id=product_id,
        timestamp=datetime.utcnow()
    ))
    db.session.commit()


def get_related_products(user_id: int, product_id: int) -> List[Product]:
    """Get related products based on user preferences."""
    subquery = (
        db.session.query(UserPreference.category_id, UserPreference.interest_level)
        .filter(UserPreference.user_id == user_id)
        .subquery()
    )

    return (
        db.session.query(Product)
        .join(subquery, Product.category_id == subquery.c.category_id)
        .filter(Product.id != product_id, Product.stock > 0)
        .order_by(desc(subquery.c.interest_level), desc(Product.avg_rating))
        .limit(5)
        .all()
    )


def get_recommended_products(user_id: int) -> List[Product]:
    """Get recommended products based on user preferences."""
    subquery = (
        db.session.query(UserPreference.category_id, UserPreference.interest_level)
        .filter(UserPreference.user_id == user_id)
        .subquery()
    )

    return (
        db.session.query(Product)
        .join(subquery, Product.category_id == subquery.c.category_id)
        .filter(Product.stock > 0)
        .order_by(desc(subquery.c.interest_level), desc(Product.avg_rating))
        .limit(10)
        .all()
    )
