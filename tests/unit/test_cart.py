import random
import unittest

from flask_login import login_user

from app import create_app
from config import AppConfig
from modules.db.database import db
from modules.db.models import User, Cart, Goods


class TestCart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        AppConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        cls.app = create_app(AppConfig)

        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        db.init_db()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.engine.dispose()
        cls.app_context.pop()

    def setUp(self):
        self.client = self.app.test_client()
        self.session = db.session
        self.session.begin()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def test_cart_info_empty(self):
        with self.app.test_request_context():
            # Test for unauthenticated user
            total_items, total_amount, discount_percentage = Cart.cart_info()
            self.assertEqual(total_items, 0)
            self.assertEqual(total_amount, 0)
            self.assertEqual(discount_percentage, 0)

            # Test for authenticated user with empty cart
            user = User(username=f'user_{random.randint(0, 123456)}',
                        email=f'{random.randint(0, 123456)}@example.com',
                        password=f'password_{random.randint(0, 123456)}')
            self.session.add(user)
            self.session.commit()

            login_user(user)
            total_items, total_amount, discount_percentage = Cart.cart_info()
            self.assertEqual(total_items, 0)
            self.assertEqual(total_amount, 0)
            self.assertEqual(discount_percentage, 0)

    def test_total_quantity(self):
        with self.app.test_request_context():
            user = User(username=f'user_{random.randint(0, 123456)}',
                        email=f'{random.randint(0, 123456)}@example.com',
                        password=f'password_{random.randint(0, 123456)}')
            goods = Goods(samplename='Test Product', price=10.0)
            self.session.add_all([user, goods])
            self.session.commit()

            cart = Cart(user_id=user.id, goods_id=goods.id, quantity=5, price=goods.price)
            self.session.add(cart)
            self.session.commit()

            login_user(user)
            total_quantity = Cart.total_quantity()
            self.assertEqual(total_quantity, 5)


if __name__ == '__main__':
    unittest.main()
