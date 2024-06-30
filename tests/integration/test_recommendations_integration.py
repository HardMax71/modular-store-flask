import unittest

from modules.db.database import db, Base
from modules.db.models import RecentlyViewedProduct, Goods, UserPreference, Category, Review
from modules.recommendations import update_recently_viewed_products, get_related_products, get_recommended_products
from tests.base_test import BaseTest
from tests.util import create_user


class TestRecommendationsIntegration(BaseTest):

    def setUp(self):
        super().setUp()

        # Clear all tables
        for table in reversed(Base.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()

        # Create test data
        self.user = create_user(self)
        self.category1 = Category(name='Category 1')
        self.category2 = Category(name='Category 2')
        self.goods1 = Goods(samplename='Goods 1', category=self.category1, description="1", stock=10)
        self.goods2 = Goods(samplename='Goods 2', category=self.category2, description="2", stock=5)

        db.session.add_all([self.user, self.category1, self.category2, self.goods1, self.goods2])
        db.session.commit()

    def test_update_recently_viewed_products(self):
        update_recently_viewed_products(self.user.id, self.goods1.id)
        recently_viewed = RecentlyViewedProduct.query.filter_by(user_id=self.user.id, goods_id=self.goods1.id).first()
        self.assertIsNotNone(recently_viewed)

    def test_get_related_products(self):
        # Add user preference
        user_preference = UserPreference(user_id=self.user.id, category_id=self.category2.id, interest_level=5)
        db.session.add(user_preference)
        db.session.commit()

        # Add some ratings to affect avg_rating
        review1 = Review(user_id=self.user.id, goods_id=self.goods1.id, rating=3)
        review2 = Review(user_id=self.user.id, goods_id=self.goods2.id, rating=5)
        db.session.add_all([review1, review2])
        db.session.commit()

        related_products = get_related_products(self.user.id, self.goods1.id)
        print(f"Related products: {related_products}")  # Debug print
        self.assertGreater(len(related_products), 0, "No related products found")
        self.assertIn(self.goods2, related_products, f"Expected {self.goods2} to be in related products")

    def test_get_recommended_products(self):
        # Add user preferences
        user_preference1 = UserPreference(user_id=self.user.id, category_id=self.category1.id, interest_level=3)
        user_preference2 = UserPreference(user_id=self.user.id, category_id=self.category2.id, interest_level=5)
        db.session.add_all([user_preference1, user_preference2])
        db.session.commit()

        # Add some ratings to affect avg_rating
        review1 = Review(user_id=self.user.id, goods_id=self.goods1.id, rating=3)
        review2 = Review(user_id=self.user.id, goods_id=self.goods2.id, rating=5)
        db.session.add_all([review1, review2])
        db.session.commit()

        recommended_products = get_recommended_products(self.user.id)
        print(f"Recommended products: {recommended_products}")  # Debug print
        self.assertGreater(len(recommended_products), 0, "No recommended products found")
        self.assertIn(self.goods1, recommended_products, f"Expected {self.goods1} to be in recommended products")
        self.assertIn(self.goods2, recommended_products, f"Expected {self.goods2} to be in recommended products")


if __name__ == '__main__':
    unittest.main()
