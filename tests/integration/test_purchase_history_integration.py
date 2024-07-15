import unittest

from flask import url_for
from flask_login import login_user, logout_user

from modules.db.models import Purchase, ShippingMethod, Address, Product, ShippingAddress, Cart
from modules.purchase_history.utils import save_purchase_history
from tests.base_test import BaseTest
from tests.util import create_user


class TestPurchaseHistoryIntegration(BaseTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=True, define_load_user=True)

    def setUp(self):
        super().setUp()
        self.user = create_user(self)
        self.product = Product(samplename='Test Product', price=10, stock=10, description='Test description')
        self.shipping_method = ShippingMethod(name='Standard', price=5)
        self.session.add_all([self.user, self.product, self.shipping_method])
        self.session.commit()

        self.address = Address(
            user_id=self.user.id, address_line1='123 Test St', city='Test City',
            state='TS', zip_code='12345', country='Testland'
        )
        self.session.add(self.address)
        self.session.commit()

        self.purchase = Purchase(user_id=self.user.id, total_price=15, discount_amount=0, delivery_fee=5,
                                 status='Pending', tracking_number='123', shipping_method='Standard',
                                 payment_method='Credit Card', payment_id='123')
        self.session.add(self.purchase)
        self.session.commit()

        shipping_address = ShippingAddress(
            purchase_id=self.purchase.id, address_line1=self.address.address_line1,
            address_line2=self.address.address_line2, city=self.address.city,
            state=self.address.state, zip_code=self.address.zip_code,
            country=self.address.country
        )
        self.session.add(shipping_address)
        self.session.commit()

    def test_purchase_history_flow(self):
        # Saving initial stock to compare later - after cancelling the order
        start_qty: int = self.product.stock

        # Create a purchase
        cart_item = Cart(user_id=self.user.id, product_id=self.product.id,
                         quantity=1, price=self.product.price)
        self.session.add(cart_item)
        self.session.commit()

        cart_items = [cart_item]

        with self.app.test_request_context():
            login_user(self.user)
            # creating a purchase with 1 item, qty = 1, stock will be reduced by 1
            purchase = save_purchase_history(
                self.session, cart_items,
                self.address.id, self.shipping_method.id, 'Credit Card', '123'
            )

        # Test purchase history view
        response = self.client.get(url_for('purchase_history.purchase_history'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Order', response.data)

        # Test purchase details view
        with self.app.test_request_context():
            response = self.client.get(url_for('purchase_history.purchase_details', purchase_id=purchase.id))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Product', response.data)
        self.assertIn(b'123 Test St', response.data)
        self.assertIn(b'Pending', response.data)

        # Test cancel order
        response = self.client.post(url_for('purchase_history.cancel_order', purchase_id=purchase.id),
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Order cancelled successfully', response.data)

        # Verify the order status has been updated
        updated_purchase = self.session.query(Purchase).filter_by(id=purchase.id).first()
        self.assertEqual(updated_purchase.status, 'Cancelled')

        # Verify that the stock has been updated - just to be sure
        self.session.refresh(self.product)
        # Since the order was cancelled, the stock should be increased by 1, see line 61
        self.assertEqual(start_qty, self.product.stock)

        # Try to cancel the order again (should fail)
        response = self.client.post(url_for('purchase_history.cancel_order', purchase_id=purchase.id),
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'This order cannot be cancelled', response.data)

        # Verify that the purchase history page still loads after cancellation
        response = self.client.get(url_for('purchase_history.purchase_history'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cancelled', response.data)

    def test_unauthorized_access(self):
        # Create a purchase for another user
        true_other = create_user(self)
        other_user = create_user(self)

        cart_item = Cart(user_id=self.user.id, product_id=self.product.id,
                         quantity=1, price=self.product.price)
        self.session.add(cart_item)
        self.session.commit()

        cart_items = [cart_item]

        with self.app.test_request_context():
            # saving purchase history under true owner
            login_user(true_other)
            save_purchase_history(
                self.session, cart_items,
                self.address.id, self.shipping_method.id, 'Credit Card', '456'
            )
            logout_user()

            # logging in under another user
            login_user(other_user)

        # Try to access the purchase details of another user
        true_user_purchase = self.session.query(Purchase).filter_by(user_id=true_other.id).first()
        response = self.client.get(url_for('purchase_history.purchase_details', purchase_id=true_user_purchase.id),
                                   follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"You don&#39;t have permission to view this purchase", response.data)

        # Try to cancel the order of another user
        response = self.client.post(url_for('purchase_history.cancel_order', purchase_id=true_user_purchase.id),
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"You don&#39;t have permission to cancel this order", response.data)


if __name__ == '__main__':
    unittest.main()
