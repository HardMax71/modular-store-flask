import unittest

from flask_login import login_user

from modules.db.models import Cart, Goods
from tests.base_test import BaseTest
from tests.util import create_user


class TestCartIntegration(BaseTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=True,
                           define_load_user=True)

    def test_cart_info_empty(self):
        user = create_user(self)
        with self.app.test_request_context():
            with self.app.test_client():
                # Test for unauthenticated user
                total_items, total_amount, discount_percentage = Cart.cart_info()
                self.assertEqual(total_items, 0)
                self.assertEqual(total_amount, 0)
                self.assertEqual(discount_percentage, 0)

                # Test for authenticated user with empty cart
                login_user(user)
                total_items, total_amount, discount_percentage = Cart.cart_info()
                self.assertEqual(total_items, 0)
                self.assertEqual(total_amount, 0)
                self.assertEqual(discount_percentage, 0)

    def test_total_quantity(self):
        user = create_user(self)
        with self.app.test_request_context():
            with self.app.test_client():
                goods = Goods(samplename='Test Product', price=10.0)
                self.session.add_all([goods])
                self.session.commit()

                cart = Cart(user_id=user.id, goods_id=goods.id, quantity=5, price=goods.price)
                self.session.add(cart)
                self.session.commit()

                login_user(user)
                total_quantity = Cart.total_quantity()
                self.assertEqual(total_quantity, 5)


if __name__ == '__main__':
    unittest.main()
