# /modular_store_backend/tests/unit/test_wishlists.py
import unittest

from modular_store_backend.modules.db.models import Wishlist, Product
from modular_store_backend.modules.wishlists.utils import (
    get_product_selection_options, item_exists_in_wishlist, remove_item_from_wishlist, add_item_to_wishlist
)
from modular_store_backend.tests.base_test import BaseTest
from modular_store_backend.tests.util import create_user


class TestWishlistsUnit(BaseTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=False, define_load_user=True)

    def create_product(self):
        product = Product(samplename='Test Product', price=1000)
        self.session.add(product)
        self.session.commit()
        return product

    def test_get_variant_options(self):
        json_data = '{"size": "M", "color": "blue"}'
        result = get_product_selection_options(json_data)
        self.assertEqual(result, {"size": "M", "color": "blue"})

    def test_get_variant_options_empty(self):
        result = get_product_selection_options(None)
        self.assertEqual(result, {})

    def test_is_wishlist_item_exists(self):
        user = create_user(self)
        product = self.create_product()
        wishlist_item = Wishlist(user_id=user.id, product_id=product.id)
        self.session.add(wishlist_item)
        self.session.commit()

        result = item_exists_in_wishlist(user.id, product.id)
        self.assertIsNotNone(result)

    def test_is_wishlist_item_not_exists(self):
        user = create_user(self)
        product = self.create_product()

        result = item_exists_in_wishlist(user.id, product.id)
        self.assertIsNone(result)

    def test_remove_from_wishlist(self):
        user = create_user(self)
        product = self.create_product()
        wishlist_item = Wishlist(user_id=user.id, product_id=product.id)
        self.session.add(wishlist_item)
        self.session.commit()

        remove_item_from_wishlist(user.id, product.id)
        result = self.session.query(Wishlist).filter_by(user_id=user.id, product_id=product.id).first()
        self.assertIsNone(result)

    def test_add_wishlist_item(self):
        user = create_user(self)
        product = self.create_product()
        variant_options = {"size": "L", "color": "red"}

        add_item_to_wishlist(user.id, product.id, variant_options)
        result = self.session.query(Wishlist).filter_by(user_id=user.id, product_id=product.id).first()
        self.assertIsNotNone(result)
        self.assertEqual(result.variant_options, '{"size": "L", "color": "red"}')


if __name__ == '__main__':
    unittest.main()
