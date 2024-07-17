import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import stripe
from flask import url_for, Flask
from flask_login import login_user

from modules.carts.utils import create_line_items_for_payment, get_stripe_acc_for_customer_by_stripe_customer_id
from modules.db.models import Cart, Product, ShippingMethod, Address, Purchase, UserDiscount, Discount, PurchaseItem
from tests.base_test import BaseTest
from tests.util import create_user


class TestCartIntegration(BaseTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=True, define_load_user=True)

    def setUp(self):
        super().setUp()
        self.user = create_user(self)
        self.product = Product(samplename='Test Product', price=1000, stock=10)
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
        with self.app.test_request_context():
            login_user(self.user)
            total_items, total_amount, discount_percentage = Cart.cart_info()
            self.assertEqual(total_items, 0)
            self.assertEqual(total_amount, 0)
            self.assertEqual(discount_percentage, 0)

    def test_cart_info_with_items(self):
        with self.app.test_request_context():
            login_user(self.user)

            # Add items to cart
            cart_item1 = Cart(user_id=self.user.id, product_id=self.product.id, quantity=2, price=self.product.price)
            cart_item2 = Cart(user_id=self.user.id, product_id=self.product.id, quantity=1, price=self.product.price)
            self.session.add_all([cart_item1, cart_item2])
            self.session.commit()

            total_items, total_amount, discount_percentage = Cart.cart_info()
            self.assertEqual(total_items, 3)
            self.assertEqual(total_amount, 3000)
            self.assertEqual(discount_percentage, 0)

    def test_total_quantity(self):
        with self.app.test_request_context():
            login_user(self.user)

            # Add items to cart
            cart_item1 = Cart(user_id=self.user.id, product_id=self.product.id, quantity=2, price=self.product.price)
            cart_item2 = Cart(user_id=self.user.id, product_id=self.product.id, quantity=3, price=self.product.price)
            self.session.add_all([cart_item1, cart_item2])
            self.session.commit()

            total_quantity = Cart.total_quantity()
            self.assertEqual(total_quantity, 5)

    def test_add_to_cart(self):
        with self.app.test_request_context():
            login_user(self.user)

            response = self.client.post(url_for('carts.add_to_cart_route'), data={
                'product_id': self.product.id,
                'quantity': 2
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Item added to cart', response.data)

            cart_item = self.session.query(Cart).filter_by(user_id=self.user.id, product_id=self.product.id).first()
            self.assertIsNotNone(cart_item)
            self.assertEqual(cart_item.quantity, 2)

    def test_add_to_cart_exceed_stock(self):
        with self.app.test_request_context():
            login_user(self.user)

            response = self.client.post(url_for('carts.add_to_cart_route'), data={
                'product_id': self.product.id,
                'quantity': 15  # Exceeds stock of 10
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Not enough stock available for this product.', response.data)

    def test_view_cart(self):
        with self.app.test_request_context():
            login_user(self.user)

            cart_item = Cart(user_id=self.user.id, product_id=self.product.id, quantity=2, price=self.product.price)
            self.session.add(cart_item)
            self.session.commit()

            response = self.client.get(url_for('carts.cart'))
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Test Product', response.data)
            self.assertIn(b'20.00', response.data)  # 2 * 10.00

    def test_update_cart(self):
        with self.app.test_request_context():
            login_user(self.user)

            cart_item = Cart(user_id=self.user.id, product_id=self.product.id, quantity=2, price=self.product.price)
            self.session.add(cart_item)
            self.session.commit()

            response = self.client.post(url_for('carts.update_cart_route'), data={
                'cart_item_id': cart_item.id,
                'quantity': 3
            })
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data['status'])
            self.assertEqual(data['cart_items'], 3)

            updated_cart_item = self.session.get(Cart, cart_item.id)
            self.assertEqual(updated_cart_item.quantity, 3)

    def test_update_cart_exceed_stock(self):
        with self.app.test_request_context():
            login_user(self.user)

            cart_item = Cart(user_id=self.user.id, product_id=self.product.id, quantity=2, price=self.product.price)
            self.session.add(cart_item)
            self.session.commit()

            response = self.client.post(url_for('carts.update_cart_route'), data={
                'cart_item_id': cart_item.id,
                'quantity': 15  # Exceeds stock of 10
            })
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertFalse(data['status'])
            self.assertIn('Requested quantity exceeds available stock', data['message'])

    def test_remove_from_cart(self):
        with self.app.test_request_context():
            login_user(self.user)

            cart_item = Cart(user_id=self.user.id, product_id=self.product.id, quantity=2, price=self.product.price)
            self.session.add(cart_item)
            self.session.commit()

            response = self.client.get(url_for('carts.remove_from_cart_route', cart_item_id=cart_item.id),
                                       follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Item removed from cart', response.data)

            removed_item = self.session.get(Cart, cart_item.id)
            self.assertIsNone(removed_item)

    def test_checkout_get(self):
        with self.app.test_request_context():
            login_user(self.user)

            cart_item = Cart(user_id=self.user.id, product_id=self.product.id, quantity=2, price=self.product.price)
            self.session.add(cart_item)
            self.session.commit()

            response = self.client.get(url_for('carts.checkout'))
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Checkout', response.data)
            self.assertIn(b'Test Product', response.data)

    @patch('stripe.checkout.Session.create')
    def test_checkout_post(self, mock_session_create):
        mock_session_create.return_value = MagicMock(id='test_session_id', url='http://test.com')

        with self.app.test_request_context():
            login_user(self.user)

            cart_item = Cart(user_id=self.user.id, product_id=self.product.id, quantity=2, price=self.product.price)
            self.session.add(cart_item)
            self.session.commit()

            response = self.client.post(url_for('carts.checkout'), data={
                'shipping_address': self.address.id,
                'shipping_method': self.shipping_method.id,
            })
            self.assertEqual(response.status_code, 302)  # Redirect to Stripe checkout
            self.assertTrue(response.location.startswith('/payment_success?order_id=1'))

    def test_order_confirmation(self):
        with self.app.test_request_context():
            login_user(self.user)

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
            self.session.flush()

            # Create purchase items
            purchase_item = PurchaseItem(
                purchase_id=purchase.id,
                product_id=self.product.id,
                quantity=3,
                price=self.product.price
            )
            self.session.add(purchase_item)
            self.session.commit()

            response = self.client.get(url_for('carts.order_confirmation'))

            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Order Confirmation', response.data)
            self.assertIn(b'35.00', response.data)  # Total price
            self.assertIn(b'5.00', response.data)  # Delivery fee
            self.assertIn(b'Credit Card', response.data)  # Payment method
            self.assertIn(b'Test Product', response.data)
            self.assertIn(b'30.00', response.data)  # 3 * 10.00
            self.assertIn(b'<td>3</td>', response.data)  # Quantity: 3

    def test_apply_discount_code(self):
        with self.app.test_request_context():
            login_user(self.user)

            # Create a valid discount
            valid_discount = Discount(
                code='VALID10',
                percentage=10,
                start_date=datetime.now().date(),
                end_date=(datetime.now() + timedelta(days=30)).date()
            )
            self.session.add(valid_discount)

            # Create an expired discount
            expired_discount = Discount(
                code='EXPIRED10',
                percentage=10,
                start_date=(datetime.now() - timedelta(days=60)).date(),
                end_date=(datetime.now() - timedelta(days=30)).date()
            )
            self.session.add(expired_discount)

            # Add items to the user's cart
            cart_item = Cart(user_id=self.user.id, product_id=self.product.id, quantity=2, price=self.product.price)
            self.session.add(cart_item)
            self.session.commit()

            # Test valid discount code
            response = self.client.post(url_for('main.apply_discount'), data={
                'discount_code': 'VALID10'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Discount code applied successfully', response.data)

            # Check if UserDiscount has been created
            user_discount = self.session.query(UserDiscount).filter_by(user_id=self.user.id,
                                                                       discount_id=valid_discount.id).first()
            self.assertIsNotNone(user_discount)

            # Test expired discount code
            response = self.client.post(url_for('main.apply_discount'), data={
                'discount_code': 'EXPIRED10'
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

        customer = get_stripe_acc_for_customer_by_stripe_customer_id(self.user)

        mock_create.assert_called_once()
        self.assertEqual(customer.id, 'cus_123')
        self.assertEqual(self.user.stripe_customer_id, 'cus_123')

        # Test case when user has Stripe customer ID
        self.user.stripe_customer_id = 'cus_456'
        mock_retrieve.return_value = MagicMock(id='cus_456')

        customer = get_stripe_acc_for_customer_by_stripe_customer_id(self.user)

        mock_retrieve.assert_called_once_with('cus_456')
        mock_modify.assert_called_once()
        self.assertEqual(customer.id, 'cus_456')

    def test_create_line_items_for_payment(self):
        cart_items = [
            Cart(user_id=self.user.id, product_id=self.product.id, quantity=2, price=self.product.price),
            Cart(user_id=self.user.id, product_id=self.product.id, quantity=1, price=self.product.price)
        ]
        self.session.add_all(cart_items)
        self.session.commit()

        line_items = create_line_items_for_payment(cart_items, self.shipping_method)

        self.assertEqual(len(line_items), 3)  # 2 product + 1 shipping
        self.assertEqual(line_items[0]['price_data']['product_data']['name'], 'Test Product')
        self.assertEqual(line_items[0]['price_data']['unit_amount'], 1000)
        self.assertEqual(line_items[0]['quantity'], 2)
        self.assertEqual(line_items[1]['price_data']['product_data']['name'], 'Test Product')
        self.assertEqual(line_items[1]['price_data']['unit_amount'], 1000)
        self.assertEqual(line_items[1]['quantity'], 1)
        self.assertEqual(line_items[2]['price_data']['product_data']['name'], 'Shipping: Standard')
        self.assertEqual(line_items[2]['price_data']['unit_amount'], 500)

    def test_cart_subtotal(self):
        with self.app.test_request_context():
            login_user(self.user)

            # Add items to cart
            cart_item1 = Cart(user_id=self.user.id, product_id=self.product.id, quantity=2, price=self.product.price)
            cart_item2 = Cart(user_id=self.user.id, product_id=self.product.id, quantity=1, price=self.product.price)
            self.session.add_all([cart_item1, cart_item2])
            self.session.commit()

            subtotal = Cart.subtotal()
            self.assertEqual(subtotal, 3000)  # (1000 * 2) + (1000 * 1)

    def test_cart_info_with_discount(self):
        with self.app.test_request_context():
            login_user(self.user)

            # Create a discount
            discount = Discount(code='TEST20', percentage=20,
                                start_date=datetime.now().date(),
                                end_date=(datetime.now() + timedelta(days=30)).date())
            self.session.add(discount)
            self.session.commit()

            # Add items to cart
            cart_item = Cart(user_id=self.user.id, product_id=self.product.id, quantity=2, price=self.product.price)
            self.session.add(cart_item)

            # Apply discount to user
            user_discount = UserDiscount(user_id=self.user.id, discount_id=discount.id)
            self.session.add(user_discount)
            self.session.commit()

            total_items, total_amount, max_discount = Cart.cart_info()
            self.assertEqual(total_items, 2)
            self.assertEqual(total_amount, 1600)  # 2000 - 20% discount
            self.assertEqual(max_discount, 20)

    def test_update_stock(self):
        # Set initial stock
        self.product.stock = 10
        self.session.commit()

        # Update stock
        Cart.update_stock(self.product.id, 3)

        # Check updated stock
        updated_product = self.session.get(Product, self.product.id)
        self.assertEqual(updated_product.stock, 7)

    def test_add_to_cart_with_variant(self):
        with self.app.test_request_context():
            login_user(self.user)

            variant_options = {'size': 'L', 'color': 'Blue'}
            response = self.client.post(url_for('carts.add_to_cart_route'), data={
                'product_id': self.product.id,
                'quantity': 1,
                'variant_options': json.dumps(variant_options)
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Item added to cart', response.data)

            cart_item = self.session.query(Cart).filter_by(
                user_id=self.user.id,
                product_id=self.product.id
            ).first()
            self.assertIsNotNone(cart_item)
            self.assertEqual(cart_item.quantity, 1)

            # Parse the stored variant_options
            stored_options = json.loads(cart_item.variant_options)
            self.assertIsInstance(stored_options, dict)
            self.assertEqual(stored_options.get('options'), json.dumps(variant_options))

    def test_add_existing_item_to_cart(self):
        with self.app.test_request_context():
            login_user(self.user)

            # Add item to cart initially
            self.client.post(url_for('carts.add_to_cart_route'), data={
                'product_id': self.product.id,
                'quantity': 1
            })

            # Add same item again
            response = self.client.post(url_for('carts.add_to_cart_route'), data={
                'product_id': self.product.id,
                'quantity': 2
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Item added to cart.', response.data)

            cart_item = self.session.query(Cart).filter_by(user_id=self.user.id, product_id=self.product.id).first()
            self.assertEqual(cart_item.quantity, 3)

    def test_view_empty_cart(self):
        with self.app.test_request_context():
            login_user(self.user)

            response = self.client.get(url_for('carts.cart'))
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Your cart is empty', response.data)

    def test_remove_nonexistent_item_from_cart(self):
        with self.app.test_request_context():
            login_user(self.user)

            response = self.client.get(url_for('carts.remove_from_cart_route', cart_item_id=999),
                                       follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Item not found in cart', response.data)

    @patch('modules.carts.views.stripe')
    @patch('modules.carts.utils.stripe')
    @patch('modules.carts.utils.save_purchase_history')
    def test_checkout_with_discount(self, mock_save_purchase, mock_stripe_utils, mock_stripe_views):
        # Set up mock stripe functionality
        mock_customer = MagicMock(id='cus_test123')
        mock_stripe_utils.Customer.create.return_value = mock_customer
        mock_stripe_utils.Customer.retrieve.return_value = mock_customer
        mock_stripe_utils.Customer.modify.return_value = mock_customer

        mock_session = MagicMock(id='ses_test123', url='http://test.com')
        mock_stripe_views.checkout.Session.create.return_value = mock_session

        # Mock save_purchase_history to return a valid Purchase object
        mock_purchase = Purchase(
            id=1,
            user_id=self.user.id,
            date=datetime.now(),
            total_price=2000,
            payment_method='test_payment',
            payment_id='test_12345'
        )
        mock_save_purchase.return_value = mock_purchase

        with self.app.test_request_context():
            with self.client:
                login_user(self.user)

                # Create a discount and apply it to the user
                discount = Discount(code='TEST10', percentage=10,
                                    start_date=datetime.now().date(),
                                    end_date=(datetime.now() + timedelta(days=30)).date())
                self.session.add(discount)
                self.session.commit()

                user_discount = UserDiscount(user_id=self.user.id, discount_id=discount.id)
                self.session.add(user_discount)

                # Add item to cart
                cart_item = Cart(user_id=self.user.id, product_id=self.product.id, quantity=2, price=self.product.price)
                self.session.add(cart_item)
                self.session.commit()

                # Ensure shipping method exists
                if not hasattr(self, 'shipping_method'):
                    self.shipping_method = ShippingMethod(name='Standard', price=500)
                    self.session.add(self.shipping_method)
                    self.session.commit()

                response = self.client.post(url_for('carts.checkout'), data={
                    'shipping_address': self.address.id,
                    'shipping_method': self.shipping_method.id,
                })

                # Check redirect to payment success
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.location.startswith('/payment_success?order_id='))

                # Verify purchase was saved
                mock_save_purchase.assert_called_once()

                # Verify cart was cleared
                cart_items = self.session.query(Cart).filter_by(user_id=self.user.id).all()
                self.assertEqual(len(cart_items), 0)

    def test_apply_invalid_discount_code(self):
        with self.app.test_request_context():
            login_user(self.user)

            response = self.client.post(url_for('main.apply_discount'), data={
                'discount_code': 'INVALID'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Invalid discount code', response.data)

    def test_apply_discount_code_twice(self):
        with self.app.test_request_context():
            login_user(self.user)

            # Create a valid discount
            valid_discount = Discount(
                code='VALID10',
                percentage=10,
                start_date=datetime.now().date(),
                end_date=(datetime.now() + timedelta(days=30)).date()
            )
            self.session.add(valid_discount)
            self.session.commit()

            # Apply discount first time
            self.client.post(url_for('main.apply_discount'), data={'discount_code': 'VALID10'})

            # Try to apply the same discount again
            response = self.client.post(url_for('main.apply_discount'), data={'discount_code': 'VALID10'},
                                        follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'You have already used this discount code', response.data)

    def test_create_line_items_for_payment_with_multiple_products(self):
        product2 = Product(samplename='Test Product 2', price=1500, stock=5)
        self.session.add(product2)
        self.session.commit()

        cart_items = [
            Cart(user_id=self.user.id, product_id=self.product.id, quantity=2, price=self.product.price),
            Cart(user_id=self.user.id, product_id=product2.id, quantity=1, price=product2.price)
        ]
        self.session.add_all(cart_items)
        self.session.commit()

        line_items = create_line_items_for_payment(cart_items, self.shipping_method)

        self.assertEqual(len(line_items), 3)  # 2 products + 1 shipping
        self.assertEqual(line_items[0]['price_data']['product_data']['name'], 'Test Product')
        self.assertEqual(line_items[0]['price_data']['unit_amount'], 1000)
        self.assertEqual(line_items[0]['quantity'], 2)
        self.assertEqual(line_items[1]['price_data']['product_data']['name'], 'Test Product 2')
        self.assertEqual(line_items[1]['price_data']['unit_amount'], 1500)
        self.assertEqual(line_items[1]['quantity'], 1)
        self.assertEqual(line_items[2]['price_data']['product_data']['name'], 'Shipping: Standard')
        self.assertEqual(line_items[2]['price_data']['unit_amount'], 500)

    def test_checkout_empty_cart(self):
        with self.app.test_request_context():
            login_user(self.user)
            response = self.client.get(url_for('carts.checkout'))
            self.assertEqual(response.status_code, 302)  # Redirect
            self.assertIn('cart', response.location)

    def test_checkout_no_address(self):
        with self.app.test_request_context():
            login_user(self.user)
            self.session.query(Address).filter_by(user_id=self.user.id).delete()
            self.session.commit()
            cart_item = Cart(user_id=self.user.id, product_id=self.product.id, quantity=1, price=self.product.price)
            self.session.add(cart_item)
            self.session.commit()
            response = self.client.get(url_for('carts.checkout'))
            self.assertEqual(response.status_code, 302)  # Redirect
            self.assertIn('profile', response.location)

    @patch('modules.carts.views.stripe.checkout.Session.retrieve')
    @patch('modules.carts.views.process_successful_payment')
    def test_payment_success_unpaid(self, mock_process_payment, mock_session_retrieve):
        mock_session = MagicMock(payment_status='unpaid')
        mock_session_retrieve.return_value = mock_session
        with self.app.test_request_context():
            login_user(self.user)
            response = self.client.get(url_for('carts.payment_success', session_id='test_session_id'))
            self.assertEqual(response.status_code, 302)  # Redirect
            self.assertIn('checkout', response.location)
        mock_process_payment.assert_not_called()

    @patch('modules.carts.views.stripe.checkout.Session.retrieve')
    def test_payment_success_stripe_error(self, mock_session_retrieve):
        mock_session_retrieve.side_effect = stripe.StripeError("Test error")
        with self.app.test_request_context():
            login_user(self.user)
            response = self.client.get(url_for('carts.payment_success', session_id='test_session_id'))
            self.assertEqual(response.status_code, 302)  # Redirect
            self.assertIn('checkout', response.location)

    def test_order_confirmation_no_purchase(self):
        with self.app.test_request_context():
            login_user(self.user)
            self.session.query(Purchase).filter_by(user_id=self.user.id).delete()
            self.session.commit()
            response = self.client.get(url_for('carts.order_confirmation'))
            self.assertEqual(response.status_code, 302)  # Redirect
            self.assertIn('/', response.location)  # Redirect to home page

    def test_from_json_filter_invalid_json(self):
        with self.app.test_request_context():
            result = self.app.jinja_env.filters['from_json']('invalid json')
            self.assertIsNone(result)

    def test_add_to_cart_nonexistent_product(self):
        with self.app.test_request_context():
            login_user(self.user)
            response = self.client.post(url_for('carts.add_to_cart_route'), data={
                'product_id': 9999,  # Non-existent product ID
                'quantity': 1
            })
            self.assertEqual(response.status_code, 302)  # Redirect
            self.assertIn('/products/9999', response.location)

    def test_update_cart_invalid_input(self):
        with self.app.test_request_context():
            login_user(self.user)
            response = self.client.post(url_for('carts.update_cart_route'), data={
                'cart_item_id': 'invalid',
                'quantity': 'invalid'
            })
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertFalse(data['status'])

    @patch('modules.carts.views.stripe.checkout.Session.retrieve')
    def test_payment_success_no_session_id(self, mock_session_retrieve):
        with self.app.test_request_context():
            login_user(self.user)
            response = self.client.get(url_for('carts.payment_success'))
            self.assertEqual(response.status_code, 302)  # Redirect
            self.assertIn('checkout', response.location)

    def test_init_cart(self):
        app = Flask(__name__)
        from modules.carts.views import init_cart
        init_cart(app)
        self.assertIn('carts', app.blueprints)

    # Helper method to get flashed messages
    def get_flashed_messages(self, response):
        return response.data


if __name__ == '__main__':
    unittest.main()
