import unittest

from flask_login import LoginManager
from werkzeug.security import generate_password_hash

from app import create_app
from config import AppConfig
from modules.db.database import db, Base
from modules.db.models import User, Wishlist, Goods
from modules.wishlists.utils import (
    get_variant_options, is_wishlist_item_exists, remove_from_wishlist, add_wishlist_item
)


class TestWishlistsUnit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        AppConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        cls.app = create_app(AppConfig)
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.app.config['SERVER_NAME'] = 'localhost'
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        LoginManager().init_app(cls.app)

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()
        db.session.remove()
        db.engine.dispose()

    def setUp(self):
        self.client = self.app.test_client()
        self.session = db.session
        self.session.begin()

        # Clear all tables
        for table in reversed(Base.metadata.sorted_tables):
            self.session.execute(table.delete())
        self.session.commit()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def create_user(self):
        user = User(username='testuser', email='test@example.com', password=generate_password_hash('password'))
        self.session.add(user)
        self.session.commit()
        return user

    def create_goods(self):
        goods = Goods(samplename='Test Product', price=10.0)
        self.session.add(goods)
        self.session.commit()
        return goods

    def test_get_variant_options(self):
        json_data = '{"size": "M", "color": "blue"}'
        result = get_variant_options(json_data)
        self.assertEqual(result, {"size": "M", "color": "blue"})

    def test_get_variant_options_empty(self):
        result = get_variant_options(None)
        self.assertEqual(result, {})

    def test_is_wishlist_item_exists(self):
        user = self.create_user()
        goods = self.create_goods()
        wishlist_item = Wishlist(user_id=user.id, goods_id=goods.id)
        self.session.add(wishlist_item)
        self.session.commit()

        result = is_wishlist_item_exists(user.id, goods.id, {})
        self.assertIsNotNone(result)

    def test_is_wishlist_item_not_exists(self):
        user = self.create_user()
        goods = self.create_goods()

        result = is_wishlist_item_exists(user.id, goods.id, {})
        self.assertIsNone(result)

    def test_remove_from_wishlist(self):
        user = self.create_user()
        goods = self.create_goods()
        wishlist_item = Wishlist(user_id=user.id, goods_id=goods.id)
        self.session.add(wishlist_item)
        self.session.commit()

        remove_from_wishlist(user.id, goods.id, {})
        result = Wishlist.query.filter_by(user_id=user.id, goods_id=goods.id).first()
        self.assertIsNone(result)

    def test_add_wishlist_item(self):
        user = self.create_user()
        goods = self.create_goods()
        variant_options = {"size": "L", "color": "red"}

        add_wishlist_item(user.id, goods.id, variant_options)
        result = Wishlist.query.filter_by(user_id=user.id, goods_id=goods.id).first()
        self.assertIsNotNone(result)
        self.assertEqual(result.variant_options, '{"size": "L", "color": "red"}')


if __name__ == '__main__':
    unittest.main()
