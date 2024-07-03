import unittest

from modules.db.models import PurchaseItem, ShippingMethod
from modules.purchase_history.utils import (
    calculate_subtotal, calculate_discount_amount, calculate_delivery_fee,
    calculate_total_price, calculate_items_subtotal
)


class TestPurchaseHistoryUtils(unittest.TestCase):

    def test_calculate_subtotal(self):
        cart_items = [
            PurchaseItem(id=1, quantity=2),
            PurchaseItem(id=2, quantity=1)
        ]
        original_prices = {1: 1000, 2: 1500}
        result = calculate_subtotal(cart_items, original_prices)
        self.assertEqual(result, 3500)

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
        self.assertEqual(result, 0.0)

    def test_calculate_total_price(self):
        subtotal = 10000
        discount_amount = 1000
        delivery_fee = 500
        result = calculate_total_price(subtotal, discount_amount, delivery_fee)
        self.assertEqual(result, 9500)

    def test_calculate_items_subtotal(self):
        items = [
            PurchaseItem(quantity=2, price=1000),
            PurchaseItem(quantity=1, price=1500)
        ]
        result = calculate_items_subtotal(items)
        self.assertEqual(result, 3500)


if __name__ == '__main__':
    unittest.main()
