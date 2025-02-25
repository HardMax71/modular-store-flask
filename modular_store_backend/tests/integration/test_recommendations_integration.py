# /modular_store_backend/tests/integration/test_recommendations_integration.py
import unittest

from modular_store_backend.modules.db.models import RecentlyViewedProduct, Product, UserPreference, Category, Review
from modular_store_backend.modules.recommendations import update_recently_viewed_products, get_related_products, \
    get_recommended_products
from modular_store_backend.tests.base_test import BaseTest
from modular_store_backend.tests.util import create_user


class TestRecommendationsIntegration(BaseTest):

    def setUp(self):
        super().setUp()

        # Create test data
        self.user = create_user(self)
        self.category1 = Category(name='Category 1')
        self.category2 = Category(name='Category 2')
        self.product1 = Product(samplename='Product 1', category=self.category1, description="1", stock=10)
        self.product2 = Product(samplename='Product 2', category=self.category2, description="2", stock=5)

        self.session.add_all([self.user, self.category1, self.category2, self.product1, self.product2])
        self.session.commit()

    def test_update_recently_viewed_products(self):
        update_recently_viewed_products(self.user.id, self.product1.id)
        recently_viewed = self.session.query(RecentlyViewedProduct).filter_by(user_id=self.user.id,
                                                                              product_id=self.product1.id).first()
        self.assertIsNotNone(recently_viewed)

    def test_get_related_products(self):
        # Add user preference
        user_preference = UserPreference(user_id=self.user.id, category_id=self.category2.id, interest_level=5)
        self.session.add(user_preference)
        self.session.commit()

        # Add some ratings to affect avg_rating
        review1 = Review(user_id=self.user.id, product_id=self.product1.id, rating=3)
        review2 = Review(user_id=self.user.id, product_id=self.product2.id, rating=5)
        self.session.add_all([review1, review2])
        self.session.commit()

        related_products = get_related_products(self.user.id, self.product1.id)
        print(f"Related products: {related_products}")  # Debug print
        self.assertGreater(len(related_products), 0, "No related products found")
        self.assertIn(self.product2, related_products, f"Expected {self.product2} to be in related products")

    def test_get_recommended_products(self):
        # Add user preferences
        user_preference1 = UserPreference(user_id=self.user.id, category_id=self.category1.id, interest_level=3)
        user_preference2 = UserPreference(user_id=self.user.id, category_id=self.category2.id, interest_level=5)
        self.session.add_all([user_preference1, user_preference2])
        self.session.commit()

        # Add some ratings to affect avg_rating
        review1 = Review(user_id=self.user.id, product_id=self.product1.id, rating=3)
        review2 = Review(user_id=self.user.id, product_id=self.product2.id, rating=5)
        self.session.add_all([review1, review2])
        self.session.commit()

        recommended_products = get_recommended_products(self.user.id)
        print(f"Recommended products: {recommended_products}")  # Debug print
        self.assertGreater(len(recommended_products), 0, "No recommended products found")
        self.assertIn(self.product1, recommended_products, f"Expected {self.product1} to be in recommended products")
        self.assertIn(self.product2, recommended_products, f"Expected {self.product2} to be in recommended products")


if __name__ == '__main__':
    unittest.main()
