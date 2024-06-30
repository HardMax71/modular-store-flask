import unittest

from flask import url_for
from flask_login import login_user

from modules.db.database import db
from modules.db.models import Purchase, PurchaseItem, ShippingMethod, Address, Goods, ShippingAddress
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
        self.goods = Goods(samplename='Test Product', price=10.0)
        self.shipping_method = ShippingMethod(name='Standard', price=5.0)
        db.session.add_all([self.user, self.goods, self.shipping_method])
        db.session.commit()

        self.address = Address(
            user_id=self.user.id, address_line1='123 Test St', city='Test City',
            state='TS', zip_code='12345', country='Testland'
        )
        db.session.add(self.address)
        db.session.commit()

        self.purchase = Purchase(user_id=self.user.id, total_price=15.0, discount_amount=0.0, delivery_fee=5.0,
                                 status='Completed', tracking_number='123', shipping_method='Standard',
                                 payment_method='Credit Card', payment_id=123)
        db.session.add(self.purchase)
        db.session.commit()

        shipping_address = ShippingAddress(
            purchase_id=self.purchase.id, address_line1=self.address.address_line1,
            address_line2=self.address.address_line2, city=self.address.city,
            state=self.address.state, zip_code=self.address.zip_code,
            country=self.address.country
        )
        db.session.add(shipping_address)
        db.session.commit()

    def test_purchase_history_flow(self):
        # Create a purchase
        purchase_item = PurchaseItem(goods_id=self.goods.id, purchase_id=self.purchase.id,
                                     quantity=1, price=self.goods.price)
        db.session.add(purchase_item)
        db.session.commit()

        cart_items = [purchase_item]
        original_prices = {self.goods.id: self.goods.price}

        with self.app.test_request_context():
            login_user(self.user)
            save_purchase_history(
                db.session, cart_items, original_prices,
                self.address.id, self.shipping_method.id, 'Credit Card', 123
            )

        # Test purchase history view
        response = self.client.get(url_for('purchase_history.purchase_history'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Order', response.data)

        # Test purchase details view
        purchase = Purchase.query.first()
        response = self.client.get(url_for('purchase_history.purchase_details', purchase_id=purchase.id))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Product', response.data)
        self.assertIn(b'123 Test St', response.data)

        # Test cancel order
        # TODO check why fails
        response = self.client.post(url_for('purchase_history.cancel_order', purchase_id=purchase.id),
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Order cancelled successfully', response.data)

        # Verify the order status has been updated
        updated_purchase = Purchase.query.get(purchase.id)
        self.assertEqual(updated_purchase.status, 'Cancelled')

    def test_unauthorized_access(self):
        # Create a purchase for another user
        other_user = create_user(self)

        purchase_item = PurchaseItem(goods_id=self.goods.id, purchase_id=self.purchase.id,
                                     quantity=1, price=self.goods.price)
        db.session.add(purchase_item)
        db.session.commit()

        cart_items = [purchase_item]
        original_prices = {self.goods.id: self.goods.price}

        with self.app.test_request_context():
            login_user(other_user)
            save_purchase_history(
                db.session, cart_items, original_prices,
                self.address.id, self.shipping_method.id, 'Credit Card', 456
            )

        # Try to access the purchase details of another user
        other_purchase = Purchase.query.filter_by(user_id=other_user.id).first()
        response = self.client.get(url_for('purchase_history.purchase_details', purchase_id=other_purchase.id),
                                   follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"You don't have permission to view this purchase", response.data)

        # Try to cancel the order of another user
        response = self.client.post(url_for('purchase_history.cancel_order', purchase_id=other_purchase.id),
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"You don't have permission to cancel this order", response.data)


if __name__ == '__main__':
    unittest.main()
