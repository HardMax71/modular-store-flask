import unittest
from unittest.mock import patch

from flask_login import login_user

from modular_store_backend.modules.db.models import Wishlist, Product
from modular_store_backend.tests.base_test import BaseTest
from modular_store_backend.tests.util import create_user


class MockEmailSender:
    def __init__(self):
        self.sent_notifications = False

    def send_wishlist_notifications(self):
        self.sent_notifications = True


class TestWishlistsIntegration(BaseTest):
    @classmethod
    def setUpClass(cls):
        cls.mock_email_sender = MockEmailSender()
        super().setUpClass()

    def setUp(self):
        # Reset mock email sender
        self.mock_email_sender.sent_notifications = False

    def create_product(self):
        product = Product(samplename='Test Product', price=1000)
        self.session.add(product)
        self.session.commit()
        return product

    def test_add_to_wishlist(self):
        user = create_user(self)
        product = self.create_product()

        with self.app.test_request_context():
            login_user(user)
            response = self.client.post('/wishlist', data={
                'product_id': product.id,
                'variant_options': '{"size": "M", "color": "blue"}'
            })

        self.assertEqual(response.status_code, 302)
        wishlist_item = self.session.query(Wishlist).filter_by(user_id=user.id, product_id=product.id).first()
        self.assertIsNotNone(wishlist_item)

    def test_remove_from_wishlist(self):
        user = create_user(self)
        product = self.create_product()
        wishlist_item = Wishlist(user_id=user.id, product_id=product.id,
                                 variant_options='{"size": "M", "color": "blue"}')
        self.session.add(wishlist_item)
        self.session.commit()

        with self.app.test_request_context():
            login_user(user)
            response = self.client.post('/wishlist', data={
                'product_id': product.id,
                'variant_options': '{"size": "M", "color": "blue"}'
            })

        self.assertEqual(response.status_code, 302)
        wishlist_item = self.session.query(Wishlist).filter_by(user_id=user.id, product_id=product.id).first()
        self.assertIsNone(wishlist_item)

    @patch('modular_store_backend.modules.wishlists.views.send_wishlist_notifications')
    def test_send_wishlist_notifications(self, mock_send_notifications):
        user = create_user(self)

        with self.app.test_request_context():
            login_user(user)
            response = self.client.get('/send-wishlist-notifications')

        self.assertEqual(response.status_code, 302)
        mock_send_notifications.assert_called_once()


if __name__ == '__main__':
    unittest.main()
