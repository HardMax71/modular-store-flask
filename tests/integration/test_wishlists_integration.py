import unittest
from unittest.mock import patch

from flask_login import login_user

from modules.db.models import Wishlist, Goods
from tests.base_test import BaseTest
from tests.util import create_user


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

    def create_goods(self):
        goods = Goods(samplename='Test Product', price=10.0)
        self.session.add(goods)
        self.session.commit()
        return goods

    def test_add_to_wishlist(self):
        user = create_user(self)
        goods = self.create_goods()

        with self.app.test_request_context():
            login_user(user)
            response = self.client.post('/wishlist', data={
                'goods_id': goods.id,
                'variant_options': '{"size": "M", "color": "blue"}'
            })

        self.assertEqual(response.status_code, 302)
        wishlist_item = Wishlist.query.filter_by(user_id=user.id, goods_id=goods.id).first()
        self.assertIsNotNone(wishlist_item)

    def test_remove_from_wishlist(self):
        user = create_user(self)
        goods = self.create_goods()
        wishlist_item = Wishlist(user_id=user.id, goods_id=goods.id, variant_options='{"size": "M", "color": "blue"}')
        self.session.add(wishlist_item)
        self.session.commit()

        with self.app.test_request_context():
            login_user(user)
            response = self.client.post('/wishlist', data={
                'goods_id': goods.id,
                'variant_options': '{"size": "M", "color": "blue"}'
            })

        self.assertEqual(response.status_code, 302)
        wishlist_item = Wishlist.query.filter_by(user_id=user.id, goods_id=goods.id).first()
        self.assertIsNone(wishlist_item)

    @patch('modules.wishlists.views.send_wishlist_notifications')
    def test_send_wishlist_notifications(self, mock_send_notifications):
        user = create_user(self)

        with self.app.test_request_context():
            login_user(user)
            response = self.client.get('/send-wishlist-notifications')

        self.assertEqual(response.status_code, 302)
        mock_send_notifications.assert_called_once()


if __name__ == '__main__':
    unittest.main()
