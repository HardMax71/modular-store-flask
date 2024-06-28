import random
import unittest
from unittest.mock import patch

from app import create_app
from config import AppConfig
from modules.db.database import db
from modules.db.models import User, Goods, RecentlyViewedProduct, Category, UserPreference, Review
from modules.recommendations import update_recently_viewed_products, get_related_products, get_recommended_products


class TestRecommendations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scheduler_patch = patch('modules.extensions.scheduler.start')
        cls.scheduler_mock = cls.scheduler_patch.start()

        AppConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

        cls.app = create_app(AppConfig)
        cls.client = cls.app.test_client()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

    @classmethod
    def tearDownClass(cls):
        cls.scheduler_patch.stop()
        db.session.remove()
        cls.app_context.pop()

    def setUp(self):
        db.session.begin(nested=True)

    def tearDown(self):
        db.session.rollback()

    def test_update_recently_viewed_products(self):
        user = User(username=f'user_{random.randint(0, 123456)}',
                    email=f'{random.randint(0, 123456)}@example.com',
                    password=f'password_{random.randint(0, 123456)}')
        goods = Goods(samplename='Test Product', price=10.0)
        db.session.add_all([user, goods])
        db.session.commit()

        update_recently_viewed_products(user.id, goods.id)

        recently_viewed = RecentlyViewedProduct.query.filter_by(user_id=user.id, goods_id=goods.id).first()
        self.assertIsNotNone(recently_viewed)

    def test_get_related_products(self):
        user = User(username=f'user_{random.randint(0, 123456)}',
                    email=f'{random.randint(0, 123456)}@example.com',
                    password=f'password_{random.randint(0, 123456)}')
        category1 = Category(name='Category 1')
        category2 = Category(name='Category 2')
        goods1 = Goods(samplename='Test Product 1', price=10.0, category=category1, stock=10)
        goods2 = Goods(samplename='Test Product 2', price=15.0, category=category2, stock=5)
        db.session.add_all([user, category1, category2, goods1, goods2])
        db.session.commit()

        user_preference = UserPreference(user_id=user.id, category_id=category2.id, interest_level=5)
        review1 = Review(user_id=user.id, goods_id=goods1.id, rating=3)
        review2 = Review(user_id=user.id, goods_id=goods2.id, rating=5)
        db.session.add_all([user_preference, review1, review2])
        db.session.commit()

        related_products = get_related_products(user.id, goods1.id)
        print(f"Related products: {related_products}")  # Debug print
        self.assertGreater(len(related_products), 0, "No related products found")
        self.assertIn(goods2, related_products, f"Expected {goods2} to be in related products")

    def test_get_recommended_products(self):
        user = User(username=f'user_{random.randint(0, 123456)}',
                    email=f'{random.randint(0, 123456)}@example.com',
                    password=f'password_{random.randint(0, 123456)}')
        category1 = Category(name='Category 1')
        category2 = Category(name='Category 2')
        goods1 = Goods(samplename='Test Product 1', price=10.0, category=category1, stock=10)
        goods2 = Goods(samplename='Test Product 2', price=15.0, category=category2, stock=5)
        db.session.add_all([user, category1, category2, goods1, goods2])
        db.session.commit()

        user_preference1 = UserPreference(user_id=user.id, category_id=category1.id, interest_level=3)
        user_preference2 = UserPreference(user_id=user.id, category_id=category2.id, interest_level=5)
        review1 = Review(user_id=user.id, goods_id=goods1.id, rating=3)
        review2 = Review(user_id=user.id, goods_id=goods2.id, rating=5)
        db.session.add_all([user_preference1, user_preference2, review1, review2])
        db.session.commit()

        recommended_products = get_recommended_products(user.id)
        print(f"Recommended products: {recommended_products}")  # Debug print
        self.assertGreater(len(recommended_products), 0, "No recommended products found")
        self.assertIn(goods1, recommended_products, f"Expected {goods1} to be in recommended products")
        self.assertIn(goods2, recommended_products, f"Expected {goods2} to be in recommended products")


if __name__ == '__main__':
    unittest.main()
