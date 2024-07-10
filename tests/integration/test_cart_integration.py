import json
import unittest
from datetime import datetime, timedelta
from typing import List
from unittest.mock import MagicMock, patch

from flask import url_for
from flask_login import login_user

from modules.carts.utils import create_line_items_for_payment, get_stripe_customer_for_user_by_id
from modules.db.models import Cart, Goods, ShippingMethod, Address, Purchase, UserDiscount, Discount, PurchaseItem
from tests.base_test import BaseTest
from tests.util import create_user


class TestCartIntegration(BaseTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=True,
                           define_load_user=True)

    def setUp(self):
        super().setUp()
        self.user = create_user(self)
        self.product = Goods(samplename='Test Product', price=1000, stock=10)
        self.shipping_method = ShippingMethod(name='Standard', price=500)
        self.address = Address(user_id=self.user.id, address_line1='123 Test St', city='Test City',
                               state='TS', zip_code='12345', country='Testland')
        self.session.add_all([self.product, self.shipping_method, self.address])
        self.session.commit()

    def test_cart_info_empty(self):
        # Test for unauthenticated user
        total_items, total_amount, discount_percentage = Cart.cart_info()
        self.assertEqual(total_items, 0)
        self.assertEqual(total_amount, 0)
        self.assertEqual(discount_percentage, 0)

        # Test for authenticated user with empty cart
        self.login_user_with_app_context()

        total_items, total_amount, discount_percentage = Cart.cart_info()
        self.assertEqual(total_items, 0)
        self.assertEqual(total_amount, 0)
        self.assertEqual(discount_percentage, 0)

    def test_total_quantity(self):
        with self.app.test_request_context():
            with self.app.test_client():
                login_user(self.user)

                goods = Goods(samplename='Test Product', price=1000)
                self.session.add_all([goods])
                self.session.commit()

                cart = Cart(user_id=self.user.id, goods_id=goods.id, quantity=5, price=goods.price)
                self.session.add(cart)
                self.session.commit()

                total_quantity = Cart.total_quantity()
                self.assertEqual(total_quantity, 5)

    def test_add_to_cart(self):
        self.login_user_with_app_context()

        response = self.client.post(url_for('carts.add_to_cart_route'), data={
            'goods_id': self.product.id,
            'quantity': 2
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Item added to cart', response.data)

        cart_item = self.session.query(Cart).filter_by(user_id=self.user.id, goods_id=self.product.id).first()
        self.assertIsNotNone(cart_item)
        self.assertEqual(cart_item.quantity, 2)

    def login_user_with_app_context(self):
        with self.app.test_request_context():
            with self.app.test_client():
                login_user(self.user)

    def test_view_cart(self):
        self.login_user_with_app_context()

        cart_item = Cart(user_id=self.user.id, goods_id=self.product.id, quantity=2, price=self.product.price)
        self.session.add(cart_item)
        self.session.commit()

        response = self.client.get(url_for('carts.cart'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Product', response.data)
        self.assertIn(b'20.00', response.data)  # 2 * 10.0

    def test_update_cart(self):
        self.login_user_with_app_context()

        cart_item = Cart(user_id=self.user.id, goods_id=self.product.id, quantity=2, price=self.product.price)
        self.session.add(cart_item)
        self.session.commit()

        response = self.client.post(url_for('carts.update_cart_route'), data={
            'cart_item_id': cart_item.id,
            'quantity': 3
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], True)
        self.assertEqual(data['cart_items'], 3)

    def test_remove_from_cart(self):
        self.login_user_with_app_context()

        cart_item = Cart(user_id=self.user.id, goods_id=self.product.id, quantity=2, price=self.product.price)
        self.session.add(cart_item)
        self.session.commit()

        response = self.client.get(url_for('carts.remove_from_cart_route', cart_item_id=cart_item.id),
                                   follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Item removed from cart', response.data)

        removed_item = self.session.get(Cart, cart_item.id)
        self.assertIsNone(removed_item)

    def test_checkout_get(self):
        self.login_user_with_app_context()

        cart_item = Cart(user_id=self.user.id, goods_id=self.product.id, quantity=2, price=self.product.price)
        self.session.add(cart_item)
        self.session.commit()

        response = self.client.get(url_for('carts.checkout'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Checkout', response.data)
        self.assertIn(b'Test Product', response.data)

    def test_checkout_post(self):
        self.login_user_with_app_context()

        cart_item = Cart(user_id=self.user.id, goods_id=self.product.id, quantity=2, price=self.product.price)
        self.session.add(cart_item)
        self.session.commit()

        response = self.client.post(url_for('carts.checkout'), data={
            'shipping_address': self.address.id,
            'shipping_method': self.shipping_method.id,
            'payment_method': 'credit_card',
            'card_number': '4242424242424242',
            'exp_month': '12',
            'exp_year': '2025',
            'cvc': '123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test purchase completed', response.data)

        # Check that the cart is cleared
        cart_items: List[Cart] = self.session.query(Cart).filter_by(user_id=self.user.id).all()
        self.assertEqual(len(cart_items), 0)

        # Check that a purchase was created
        purchase: Purchase = self.session.query(Purchase).filter_by(user_id=self.user.id).first()
        self.assertIsNotNone(purchase)

    def test_order_confirmation(self):
        self.login_user_with_app_context()

        # Create some products
        # (!) price in cents
        product1 = Goods(samplename='Test Product 1', price=1000, stock=10)
        product2 = Goods(samplename='Test Product 2', price=1500, stock=10)
        self.session.add_all([product1, product2])
        self.session.commit()

        # Create a purchase
        purchase = Purchase(
            user_id=self.user.id,
            total_price=3500,
            status='Completed',
            discount_amount=0,
            delivery_fee=500,
            payment_method='Credit Card'
        )
        self.session.add(purchase)
        self.session.flush()  # Flush to get the purchase id

        # Create purchase items
        purchase_item1 = PurchaseItem(
            purchase_id=purchase.id,
            goods_id=product1.id,
            quantity=2,
            price=product1.price
        )
        purchase_item2 = PurchaseItem(
            purchase_id=purchase.id,
            goods_id=product2.id,
            quantity=1,
            price=product2.price
        )
        self.session.add_all([purchase_item1, purchase_item2])
        self.session.commit()

        response = self.client.get(url_for('carts.order_confirmation'))

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Order Confirmation', response.data)

        # Check for purchase details
        self.assertIn(b'35.00', response.data)  # Total price
        self.assertIn(b'5.00', response.data)  # Delivery fee
        self.assertIn(b'Credit Card', response.data)  # Payment method

        # Check for product details
        self.assertIn(b'Test Product 1', response.data)
        self.assertIn(b'10.00', response.data)
        self.assertIn(b'<td>2</td>', response.data)  # Quantity: 2

        self.assertIn(b'Test Product 2', response.data)
        self.assertIn(b'15.00', response.data)
        self.assertIn(b'<td>1</td>', response.data)  # Quantity: 1

    def test_apply_discount_code(self):
        # Setup: Create a valid discount
        valid_discount = Discount(
            code='VALID10',
            percentage=10,
            start_date=datetime.now().date(),
            end_date=(datetime.now() + timedelta(days=30)).date()
        )
        self.session.add(valid_discount)

        # Setup: Create an expired discount
        expired_discount = Discount(
            code='EXPIRED10',
            percentage=10,
            start_date=(datetime.now() - timedelta(days=60)).date(),
            end_date=(datetime.now() - timedelta(days=30)).date()
        )
        self.session.add(expired_discount)

        # Setup: Create a future discount
        future_discount = Discount(
            code='FUTURE10',
            percentage=10,
            start_date=(datetime.now() + timedelta(days=30)).date(),
            end_date=(datetime.now() + timedelta(days=60)).date()
        )
        self.session.add(future_discount)

        # Setup: Add some items to the user's cart
        cart_item = Cart(user_id=self.user.id, goods_id=self.product.id, quantity=2, price=self.product.price)
        self.session.add(cart_item)

        self.session.commit()

        # Test 1: Invalid discount code
        response = self.client.post(url_for('main.apply_discount'), data={
            'discount_code': 'INVALID'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid discount code', response.data)

        # Test 2: Valid discount code
        response = self.client.post(url_for('main.apply_discount'), data={
            'discount_code': 'VALID10'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Discount code applied successfully', response.data)

        # Check if the cart items' prices have been updated
        updated_cart_item = self.session.query(Cart).filter_by(user_id=self.user.id).first()
        self.assertAlmostEqual(updated_cart_item.price, self.product.price * 0.9)  # checking values in cents

        # Check if UserDiscount has been created
        user_discount = self.session.query(UserDiscount).filter_by(user_id=self.user.id,
                                                                   discount_id=valid_discount.id).first()
        self.assertIsNotNone(user_discount)

        # Test 3: Try to apply the same discount code again
        response = self.client.post(url_for('main.apply_discount'), data={
            'discount_code': 'VALID10'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'You have already used this discount code', response.data)

        # Test 4: Expired discount code
        response = self.client.post(url_for('main.apply_discount'), data={
            'discount_code': 'EXPIRED10'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid discount code', response.data)

        # Test 5: Future discount code
        response = self.client.post(url_for('main.apply_discount'), data={
            'discount_code': 'FUTURE10'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid discount code', response.data)

    @patch('stripe.Customer.create')
    @patch('stripe.Customer.retrieve')
    @patch('stripe.Customer.modify')
    def test_get_stripe_customer_for_user_by_id(self, mock_modify, mock_retrieve, mock_create):
        # Test case when user has no Stripe customer ID
        self.user.stripe_customer_id = None
        mock_create.return_value = MagicMock(id='cus_123')

        customer = get_stripe_customer_for_user_by_id(self.user)

        mock_create.assert_called_once()
        self.assertEqual(customer.id, 'cus_123')
        self.assertEqual(self.user.stripe_customer_id, 'cus_123')

        # Test case when user has Stripe customer ID
        self.user.stripe_customer_id = 'cus_456'
        mock_retrieve.return_value = MagicMock(id='cus_456')

        customer = get_stripe_customer_for_user_by_id(self.user)

        mock_retrieve.assert_called_once_with('cus_456')
        mock_modify.assert_called_once()
        self.assertEqual(customer.id, 'cus_456')

    def create_test_data(self):
        product1 = Goods(samplename='Product 1', price=1000)
        product2 = Goods(samplename='Product 2', price=2000)
        self.session.add_all([product1, product2])
        self.session.commit()

        cart_items = [
            Cart(user_id=self.user.id, goods_id=product1.id, quantity=2, price=product1.price),
            Cart(user_id=self.user.id, goods_id=product2.id, quantity=1, price=product2.price)
        ]
        self.session.add_all(cart_items)
        self.session.commit()
        return cart_items

    def test_create_line_items_for_payment(self):
        cart_items = self.create_test_data()

        shipping_method = ShippingMethod(name='Express', price=1500)
        self.session.add(shipping_method)
        self.session.commit()

        # Call the function
        line_items = create_line_items_for_payment(cart_items, shipping_method)

        # Assert the results
        self.assertEqual(len(line_items), 3)  # 2 products + 1 shipping
        self.assertEqual(line_items[0]['price_data']['product_data']['name'], 'Product 1')
        self.assertEqual(line_items[0]['price_data']['unit_amount'], 1000)
        self.assertEqual(line_items[0]['quantity'], 2)
        self.assertEqual(line_items[1]['price_data']['product_data']['name'], 'Product 2')
        self.assertEqual(line_items[1]['price_data']['unit_amount'], 2000)
        self.assertEqual(line_items[1]['quantity'], 1)
        self.assertEqual(line_items[2]['price_data']['product_data']['name'], 'Shipping: Express')
        self.assertEqual(line_items[2]['price_data']['unit_amount'], 1500)
        self.assertEqual(line_items[2]['quantity'], 1)

    def test_cart_subtotal(self):
        self.create_test_data()

        # Test the subtotal
        with self.app.test_request_context():
            with self.app.test_client():
                login_user(self.user)
                subtotal = Cart.subtotal()
                self.assertEqual(subtotal, 4000)  # (1000 * 2) + (2000 * 1)

    def test_cart_info_with_discount(self):
        # Create test data
        product = Goods(samplename='Discounted Product', price=10000)
        self.session.add(product)
        self.session.commit()

        cart_item = Cart(user_id=self.user.id, goods_id=product.id, quantity=1, price=product.price)
        self.session.add(cart_item)

        discount = Discount(code='TEST10', percentage=10,
                            start_date=datetime.now().date(),
                            end_date=(datetime.now() + timedelta(days=30)).date())
        self.session.add(discount)
        self.session.commit()

        user_discount = UserDiscount(user_id=self.user.id, discount_id=discount.id)
        self.session.add(user_discount)

        self.session.commit()

        # Test cart info
        with self.app.test_request_context():
            with self.app.test_client():
                login_user(self.user)
                total_items, total_amount, max_discount = Cart.cart_info()
                self.assertEqual(total_items, 1)
                self.assertEqual(total_amount, 9000)  # 10000 - 10%
                self.assertEqual(max_discount, 10)  # 10%

    def test_update_stock(self):
        # Create test data
        product = Goods(samplename='Stock Product', price=1000, stock=10)
        self.session.add(product)
        self.session.commit()

        # Update stock
        Cart.update_stock(product.id, 3)

        # Check updated stock
        updated_product = self.session.get(Goods, product.id)
        self.assertEqual(updated_product.stock, 7)


if __name__ == '__main__':
    unittest.main()
