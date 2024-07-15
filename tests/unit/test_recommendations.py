import unittest
from unittest.mock import patch

from modules.db.database import db
from modules.db.models import Product, Category, UserPreference, Review, RecentlyViewedProduct
from modules.recommendations import update_recently_viewed_products, get_related_products, get_recommended_products
from tests.base_test import BaseTest
from tests.util import create_user


class TestRecommendations(BaseTest):
    @classmethod
    def setUpClass(cls):
        cls.scheduler_patch = patch('modules.extensions.scheduler.start')
        cls.scheduler_mock = cls.scheduler_patch.start()

        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.scheduler_patch.stop()
        super().tearDownClass()

    def generate_db_data(self):
        user = create_user(self)
        category1 = Category(name='Category 1')
        category2 = Category(name='Category 2')
        product1 = Product(samplename='Test Product 1', price=1000, category=category1, stock=10)
        product2 = Product(samplename='Test Product 2', price=1500, category=category2, stock=5)
        self.session.add_all([user, category1, category2, product1, product2])
        self.session.commit()
        return user, category1, category2, product1, product2

    def test_update_recently_viewed_products(self):
        user = create_user(self)
        product = Product(samplename='Test Product', price=1000)
        self.session.add_all([user, product])
        self.session.commit()

        update_recently_viewed_products(user.id, product.id)

        recently_viewed = self.session.query(RecentlyViewedProduct).filter_by(user_id=user.id,
                                                                              product_id=product.id).first()
        self.assertIsNotNone(recently_viewed)

    def test_get_related_products(self):
        user, category1, category2, product1, product2 = self.generate_db_data()

        user_preference = UserPreference(user_id=user.id, category_id=category2.id, interest_level=5)
        review1 = Review(user_id=user.id, product_id=product1.id, rating=3)
        review2 = Review(user_id=user.id, product_id=product2.id, rating=5)
        db.session.add_all([user_preference, review1, review2])
        db.session.commit()

        related_products = get_related_products(user.id, product1.id)
        self.assertGreater(len(related_products), 0, "No related products found")
        self.assertIn(product2, related_products, f"Expected {product2} to be in related products")

    def test_get_recommended_products(self):
        user, category1, category2, product1, product2 = self.generate_db_data()

        user_preference1 = UserPreference(user_id=user.id, category_id=category1.id, interest_level=3)
        user_preference2 = UserPreference(user_id=user.id, category_id=category2.id, interest_level=5)
        review1 = Review(user_id=user.id, product_id=product1.id, rating=3)
        review2 = Review(user_id=user.id, product_id=product2.id, rating=5)
        db.session.add_all([user_preference1, user_preference2, review1, review2])
        db.session.commit()

        recommended_products = get_recommended_products(user.id)
        self.assertGreater(len(recommended_products), 0, "No recommended products found")
        self.assertIn(product1, recommended_products, f"Expected {product1} to be in recommended products")
        self.assertIn(product2, recommended_products, f"Expected {product2} to be in recommended products")


if __name__ == '__main__':
    unittest.main()
