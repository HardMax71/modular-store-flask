# /modular_store_backend/tests/unit/test_purchase_history.py
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from modular_store_backend.modules.db.models import ShippingMethod, Cart, Address, Purchase
from modular_store_backend.modules.purchase_history.utils import (
    save_purchase_history,
    calculate_discount_amount,
    calculate_delivery_fee,
    calculate_total_price,
    generate_tracking_number,
    create_purchase_items
)


class TestPurchaseHistoryUtils(unittest.TestCase):

    def setUp(self):
        self.mock_db_session = Mock()
        self.mock_current_user = Mock(id=1, email='test@example.com', discount=10)

    def test_calculate_discount_amount(self):
        subtotal = 10000
        discount_percentage = 10.0
        result = calculate_discount_amount(subtotal, discount_percentage)
        self.assertEqual(result, 1000)

    def test_calculate_delivery_fee(self):
        shipping_method = ShippingMethod(price=500)
        result = calculate_delivery_fee(shipping_method)
        self.assertEqual(result, 500)

    def test_calculate_delivery_fee_no_method(self):
        result = calculate_delivery_fee(None)
        self.assertEqual(result, 0)

    def test_calculate_total_price(self):
        subtotal = 10000
        discount_amount = 1000
        delivery_fee = 500
        result = calculate_total_price(subtotal, discount_amount, delivery_fee)
        self.assertEqual(result, 9500)

    def test_generate_tracking_number(self):
        result = generate_tracking_number()
        self.assertTrue(result.startswith('TRACK'))
        self.assertEqual(len(result), 15)  # 'TRACK' + 10 digits

    @patch('modular_store_backend.modules.purchase_history.utils.current_user', new_callable=Mock)
    def test_save_purchase_history_no_cart_items(self, mock_current_user):
        mock_current_user.configure_mock(**self.mock_current_user.__dict__)

        with self.assertRaises(ValueError) as context:
            save_purchase_history(self.mock_db_session, [], 1, 1, 'credit_card', 'payment123')

        self.assertEqual(str(context.exception), "No cart items!")

    @patch('modular_store_backend.modules.purchase_history.utils.current_user', new_callable=Mock)
    def test_save_purchase_history_invalid_shipping_address(self, mock_current_user):
        mock_current_user.configure_mock(**self.mock_current_user.__dict__)

        self.mock_db_session.get.return_value = None
        cart_items = [Cart(price=1000, quantity=2)]

        with self.assertRaises(ValueError) as context:
            save_purchase_history(self.mock_db_session, cart_items, 1, 1, 'credit_card', 'payment123')

        self.assertEqual(str(context.exception), "Invalid shipping address ID")

    @patch('modular_store_backend.modules.purchase_history.utils.current_user', new_callable=Mock)
    @patch('modular_store_backend.modules.purchase_history.utils.datetime')
    @patch('modular_store_backend.modules.purchase_history.utils.send_email')
    def test_save_purchase_history_success(self, mock_send_email, mock_datetime, mock_current_user):
        mock_current_user.configure_mock(**self.mock_current_user.__dict__)
        mock_datetime.datetime.now.return_value = datetime(2023, 1, 1)

        self.mock_db_session.get.side_effect = [
            ShippingMethod(id=1, name='Standard', price=500),
            Address(id=1, address_line1='123 Test St', city='Test City', state='TS', zip_code='12345',
                    country='Test Country')
        ]
        cart_items = [Cart(price=1000, quantity=2)]

        result = save_purchase_history(self.mock_db_session, cart_items, 1, 1, 'credit_card', 'payment123')

        self.assertIsInstance(result, Purchase)
        self.assertEqual(result.user_id, 1)
        self.assertEqual(result.total_price, 2300)  # (1000 * 2) - 200 (discount) + 500 (shipping)
        self.assertEqual(result.discount_amount, 200)
        self.assertEqual(result.delivery_fee, 500)
        self.assertEqual(result.status, "Pending")
        self.assertEqual(result.shipping_method, "Standard")
        self.assertEqual(result.payment_method, "credit_card")
        self.assertEqual(result.payment_id, "payment123")

        mock_send_email.assert_called_once_with(
            'test@example.com',
            'Order Confirmation',
            'Thank you for your order! Your order is being processed.'
        )

    def test_create_purchase_items(self):
        cart_items = [
            Cart(product_id=1, price=1000, quantity=2),
            Cart(product_id=2, price=1500, quantity=1)
        ]
        create_purchase_items(self.mock_db_session, 1, cart_items)

        self.assertEqual(self.mock_db_session.add.call_count, 2)
        self.mock_db_session.flush.assert_called_once()


if __name__ == '__main__':
    unittest.main()
