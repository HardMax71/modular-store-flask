import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from flask import url_for
from flask_login import login_user

from modular_store_backend.modules.carts.utils import (
    process_payment, get_shipping_info, process_test_payment, process_stripe_payment,
    clear_cart, update_cart, remove_from_cart,
    add_to_cart, apply_discount_code, process_successful_payment,
    handle_unsuccessful_payment, handle_stripe_error
)
from modular_store_backend.modules.db.models import Product, Cart, ShippingMethod, Address
from modular_store_backend.tests.base_test import BaseTest
from modular_store_backend.tests.util import create_user


class TestCartUtils(BaseTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=True, define_load_user=True)

    def setUp(self):
        super().setUp()
        self.user = create_user(self)
        self.product = Product(samplename="Test Product", price=1000, stock=10)
        self.shipping_method = ShippingMethod(name="Test Method", price=500)
        self.address = Address(
            user_id=self.user.id,
            address_line1="123 Test St",
            city="Test City",
            state="Test State",
            zip_code="12345",
            country="Test Country"
        )
        self.session.add_all([self.product, self.shipping_method, self.address])
        self.session.commit()

    def test_process_payment_no_shipping_info(self):
        with self.app.test_request_context():
            login_user(self.user)
            with patch('modules.carts.utils.get_shipping_info', return_value=None):
                result = process_payment([])
                self.assertEqual(result.location, url_for('carts.checkout'))

    def test_process_test_payment(self):
        cart_item = Cart(user_id=self.user.id, product_id=self.product.id, quantity=1, price=1000)
        self.session.add(cart_item)
        self.session.commit()

        with self.app.test_request_context():
            login_user(self.user)
            result = process_test_payment([cart_item], self.address.id, self.shipping_method.id)
            self.assertIn('payment_success', result.location)

    @patch('modular_store_backend.modules.carts.utils.stripe.checkout.Session')
    def test_process_successful_payment(self, mock_session):
        mock_session.retrieve.return_value = MagicMock(
            metadata={'shipping_address_id': str(self.address.id), 'shipping_method_id': str(self.shipping_method.id)},
            payment_intent='pi_123'
        )
        cart_item = Cart(user_id=self.user.id, product_id=self.product.id, quantity=1, price=1000)
        self.session.add(cart_item)
        self.session.commit()

        with self.app.test_request_context():
            login_user(self.user)
            result = process_successful_payment(mock_session)
            self.assertIn('Purchase completed', result)

    def test_clear_cart(self):
        cart_item = Cart(user_id=self.user.id, product_id=self.product.id, quantity=1, price=1000)
        self.session.add(cart_item)
        self.session.commit()

        with self.app.test_request_context():
            login_user(self.user)
            clear_cart()
            self.assertEqual(self.session.query(Cart).count(), 0)

    def test_update_cart_success(self):
        cart_item = Cart(user_id=self.user.id, product_id=self.product.id, quantity=1, price=1000)
        self.session.add(cart_item)
        self.session.commit()

        with self.app.test_request_context():
            login_user(self.user)
            result = update_cart(cart_item.id, 2)
            self.assertTrue(result)
            self.assertEqual(cart_item.quantity, 2)
            self.assertEqual(self.product.stock, 9)

    def test_remove_from_cart(self):
        cart_item = Cart(user_id=self.user.id, product_id=self.product.id, quantity=1, price=1000)
        self.session.add(cart_item)
        self.session.commit()

        with self.app.test_request_context():
            login_user(self.user)
            result = remove_from_cart(cart_item.id)
            self.assertTrue(result)
            self.assertEqual(self.session.query(Cart).count(), 0)

    def test_add_to_cart_success(self):
        with self.app.test_request_context():
            login_user(self.user)
            result = add_to_cart(self.product, 1, {})
            self.assertTrue(result)
            self.assertEqual(self.session.query(Cart).count(), 1)

    def test_apply_discount_code_success(self):
        from modular_store_backend.modules.db.models import Discount
        discount = Discount(code="TEST10", percentage=10, start_date=datetime.now().date(),
                            end_date=datetime.now().date() + timedelta(days=30))
        self.session.add(discount)
        self.session.commit()

        cart_item = Cart(user_id=self.user.id, product_id=self.product.id, quantity=1, price=1000)
        self.session.add(cart_item)
        self.session.commit()

        with self.app.test_request_context():
            login_user(self.user)
            result = apply_discount_code("TEST10")
            self.assertEqual(result, "success")
            self.assertEqual(cart_item.price, 900)

    def test_handle_unsuccessful_payment(self):
        with self.app.test_request_context():
            result = handle_unsuccessful_payment()
            self.assertEqual(result.location, url_for('carts.checkout'))

    def test_get_shipping_info_success(self):
        with self.app.test_request_context(data={
            'shipping_address': str(self.address.id),
            'shipping_method': str(self.shipping_method.id)
        }):
            result = get_shipping_info()
            self.assertEqual(result, (self.address.id, self.shipping_method))

    @patch('modular_store_backend.modules.carts.utils.stripe')
    def test_process_stripe_payment(self, mock_stripe):
        mock_stripe.Customer.create.return_value = MagicMock(id='cust_123')
        mock_stripe.checkout.Session.create.return_value = MagicMock(url='https://stripe.com/checkout')

        cart_item = Cart(user_id=self.user.id, product_id=self.product.id, quantity=1, price=1000)
        self.session.add(cart_item)
        self.session.commit()

        with self.app.test_request_context():
            login_user(self.user)
            result = process_stripe_payment([cart_item], self.address.id, self.shipping_method)
            self.assertEqual(result.location, 'https://stripe.com/checkout')

    @patch('modular_store_backend.modules.carts.utils.stripe.StripeError', Exception)
    def test_handle_stripe_error(self):
        with self.app.test_request_context():
            result = handle_stripe_error(Exception("Test error"))
            self.assertEqual(result.location, url_for('carts.checkout'))


if __name__ == '__main__':
    unittest.main()
