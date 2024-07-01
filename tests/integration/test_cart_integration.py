import json
import unittest
from datetime import datetime, timedelta

from flask import url_for
from flask_login import login_user

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
        self.product = Goods(samplename='Test Product', price=10.0, stock=10)
        self.shipping_method = ShippingMethod(name='Standard', price=5.0)
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

                goods = Goods(samplename='Test Product', price=10.0)
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

        cart_item = Cart.query.filter_by(user_id=self.user.id, goods_id=self.product.id).first()
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

        removed_item = Cart.query.get(cart_item.id)
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
        cart_items = Cart.query.filter_by(user_id=self.user.id).all()
        self.assertEqual(len(cart_items), 0)

        # Check that a purchase was created
        purchase = Purchase.query.filter_by(user_id=self.user.id).first()
        self.assertIsNotNone(purchase)

    def test_order_confirmation(self):
        self.login_user_with_app_context()

        # Create some products
        product1 = Goods(samplename='Test Product 1', price=10.0, stock=10)
        product2 = Goods(samplename='Test Product 2', price=15.0, stock=10)
        self.session.add_all([product1, product2])
        self.session.commit()

        # Create a purchase
        purchase = Purchase(
            user_id=self.user.id,
            total_price=35.0,
            status='Completed',
            discount_amount=0,
            delivery_fee=5.0,
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

        # Clean up
        # self.session.query(PurchaseItem).delete()
        # self.session.query(Purchase).delete()
        # self.session.query(Goods).delete()
        # self.session.commit()

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
        updated_cart_item = Cart.query.filter_by(user_id=self.user.id).first()
        self.assertAlmostEqual(updated_cart_item.price, self.product.price * 0.9, places=2)

        # Check if UserDiscount has been created
        user_discount = UserDiscount.query.filter_by(user_id=self.user.id, discount_id=valid_discount.id).first()
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

        # Cleanup
        # self.session.query(UserDiscount).delete()
        # self.session.query(Discount).delete()
        # self.session.query(Cart).delete()
        # self.session.commit()


if __name__ == '__main__':
    unittest.main()
