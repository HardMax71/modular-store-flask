import unittest
import random

from flask_login import login_user

from app import create_app
from config import AppConfig
from modules.db.database import db
from modules.db.models import User, Goods, Wishlist
from modules.email import send_email, send_wishlist_notifications, send_order_confirmation_email
from flask_mail import Mail


class TestEmailFunctions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        AppConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        cls.app = create_app(AppConfig)
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        db.init_db()

        cls.mail = Mail(cls.app)

        @cls.app.login_manager.user_loader
        def load_user(user_id):
            return User.query.get(user_id)

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

    def test_send_email(self):
        with self.app.test_request_context():
            user = User(username=f'user_{random.randint(0, 123456)}',
                        email=f'{random.randint(0, 123456)}@example.com',
                        password=f'password_{random.randint(0, 123456)}')
            self.session.add(user)
            self.session.commit()

            login_user(user)

            with self.app.app_context():
                with self.mail.record_messages() as outbox:
                    send_email(user.email, "Test Subject", "Test Body")

                    self.assertEqual(len(outbox), 1)
                    self.assertEqual(outbox[0].subject, "Test Subject")
                    self.assertEqual(outbox[0].recipients, [user.email])
                    self.assertEqual(outbox[0].body, "Test Body")

    def test_send_wishlist_notifications(self):
        with self.app.test_request_context():
            user = User(username=f'user_{random.randint(0, 123456)}',
                        email=f'{random.randint(0, 123456)}@example.com',
                        password=f'password_{random.randint(0, 123456)}')
            self.session.add(user)
            self.session.commit()

            goods_on_sale = Goods(samplename='On Sale Item', price=100, onSale=1, onSalePrice=50, stock=10)
            goods_back_in_stock = Goods(samplename='Back in Stock Item', price=100, onSale=0, stock=10)
            self.session.add_all([goods_on_sale, goods_back_in_stock])
            self.session.commit()

            wishlist_item1 = Wishlist(user_id=user.id, goods_id=goods_on_sale.id)
            wishlist_item2 = Wishlist(user_id=user.id, goods_id=goods_back_in_stock.id)
            self.session.add_all([wishlist_item1, wishlist_item2])
            self.session.commit()

            login_user(user)

            with self.app.app_context():
                with self.mail.record_messages() as outbox:
                    send_wishlist_notifications()

                    self.assertEqual(len(outbox), 1)
                    self.assertEqual(outbox[0].subject, "Wishlist Items Update")
                    self.assertEqual(outbox[0].recipients, [user.email])
                    self.assertIn("On Sale Item", outbox[0].body)
                    self.assertIn("Back in Stock Item", outbox[0].body)

    def test_send_order_confirmation_email(self):
        with self.app.test_request_context():
            user = User(username=f'user_{random.randint(0, 123456)}',
                        email=f'{random.randint(0, 123456)}@example.com',
                        password=f'password_{random.randint(0, 123456)}')
            self.session.add(user)
            self.session.commit()

            login_user(user)

            with self.app.app_context():
                with self.mail.record_messages() as outbox:
                    send_order_confirmation_email(user.email, "Test User")

                    self.assertEqual(len(outbox), 1)
                    self.assertEqual(outbox[0].subject, "Order Confirmation")
                    self.assertEqual(outbox[0].recipients, [user.email])
                    self.assertIn("Thank you for your purchase", outbox[0].body)


if __name__ == '__main__':
    unittest.main()
