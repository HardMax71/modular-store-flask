import unittest

from modules.db.models import Wishlist, Goods
from modules.wishlists.utils import (
    get_variant_options, is_wishlist_item_exists, remove_from_wishlist, add_wishlist_item
)
from tests.base_test import BaseTest
from tests.util import create_user


class TestWishlistsUnit(BaseTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=False, define_load_user=True)

    def create_goods(self):
        goods = Goods(samplename='Test Product', price=1000)
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
        user = create_user(self)
        goods = self.create_goods()
        wishlist_item = Wishlist(user_id=user.id, goods_id=goods.id)
        self.session.add(wishlist_item)
        self.session.commit()

        result = is_wishlist_item_exists(user.id, goods.id, {})
        self.assertIsNotNone(result)

    def test_is_wishlist_item_not_exists(self):
        user = create_user(self)
        goods = self.create_goods()

        result = is_wishlist_item_exists(user.id, goods.id, {})
        self.assertIsNone(result)

    def test_remove_from_wishlist(self):
        user = create_user(self)
        goods = self.create_goods()
        wishlist_item = Wishlist(user_id=user.id, goods_id=goods.id)
        self.session.add(wishlist_item)
        self.session.commit()

        remove_from_wishlist(user.id, goods.id, {})
        result = Wishlist.query.filter_by(user_id=user.id, goods_id=goods.id).first()
        self.assertIsNone(result)

    def test_add_wishlist_item(self):
        user = create_user(self)
        goods = self.create_goods()
        variant_options = {"size": "L", "color": "red"}

        add_wishlist_item(user.id, goods.id, variant_options)
        result = Wishlist.query.filter_by(user_id=user.id, goods_id=goods.id).first()
        self.assertIsNotNone(result)
        self.assertEqual(result.variant_options, '{"size": "L", "color": "red"}')


if __name__ == '__main__':
    unittest.main()
