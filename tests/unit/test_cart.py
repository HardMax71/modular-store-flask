import random
import unittest
from unittest.mock import patch

from app import create_app
from config import AppConfig
from modules.db.database import db
from modules.db.models import User, Cart, Goods


class TestCart(unittest.TestCase):
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

    @patch('modules.db.models.current_user')
    def test_cart_info_empty(self, mock_current_user):
        # Test for unauthenticated user
        mock_current_user.is_authenticated = False
        total_items, total_amount, discount_percentage = Cart.cart_info()
        self.assertEqual(total_items, 0)
        self.assertEqual(total_amount, 0)
        self.assertEqual(discount_percentage, 0)

        # Test for authenticated user with empty cart
        user = User(username=f'user_{random.randint(0, 123456)}',
                    email=f'{random.randint(0, 123456)}@example.com',
                    password=f'password_{random.randint(0, 123456)}')
        db.session.add(user)
        db.session.commit()

        mock_current_user.is_authenticated = True
        mock_current_user.id = user.id
        total_items, total_amount, discount_percentage = Cart.cart_info()
        self.assertEqual(total_items, 0)
        self.assertEqual(total_amount, 0)
        self.assertEqual(discount_percentage, 0)

    @patch('modules.db.models.current_user')
    def test_total_quantity(self, mock_current_user):
        user = User(username=f'user_{random.randint(0, 123456)}',
                    email=f'{random.randint(0, 123456)}@example.com',
                    password=f'password_{random.randint(0, 123456)}')
        goods = Goods(samplename='Test Product', price=10.0)
        db.session.add_all([user, goods])
        db.session.commit()

        cart = Cart(user_id=user.id, goods_id=goods.id, quantity=5, price=goods.price)
        db.session.add(cart)
        db.session.commit()

        mock_current_user.is_authenticated = True
        mock_current_user.id = user.id
        total_quantity = Cart.total_quantity()
        self.assertEqual(total_quantity, 5)


if __name__ == '__main__':
    unittest.main()
