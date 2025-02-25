# /modular_store_backend/tests/integration/test_email_integration.py
import os
import unittest

from flask_login import login_user
from flask_mail import Mail

from modular_store_backend.modules.db.models import Product, Wishlist
from modular_store_backend.modules.email import (
    send_email, send_wishlist_notifications, send_order_confirmation_email,
    create_wishlist_message
)
from modular_store_backend.tests.base_test import BaseTest
from modular_store_backend.tests.util import create_user


class TestEmailFunctionsIntegration(BaseTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=True, define_load_user=True)
        cls.mail = Mail(cls.app)

    def setUp(self):
        super().setUp()
        self.user = create_user(self)
        with self.app.test_request_context():
            login_user(self.user)

    def test_send_email(self):
        with self.app.test_request_context():
            with self.mail.record_messages() as outbox:
                send_email(self.user.email, "Test Subject", "Test Body")

                self.assertEqual(len(outbox), 1)
                self.assertEqual(outbox[0].subject, "Test Subject")
                self.assertEqual(outbox[0].recipients, [self.user.email])
                self.assertEqual(outbox[0].body, "Test Body")

    def test_send_email_with_attachment(self):
        # Create a temporary file for attachment
        temp_file_path = os.path.abspath(os.path.join(self.app.root_path, '..', 'tests', 'test_attachment.txt'))
        os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
        with open(temp_file_path, 'w') as f:
            f.write('Test attachment content')

        with self.app.test_request_context():
            with self.mail.record_messages() as outbox:
                send_email(self.user.email, "Test Subject", "Test Body", attachments=[temp_file_path])

                self.assertEqual(len(outbox), 1)
                self.assertEqual(outbox[0].subject, "Test Subject")
                self.assertEqual(outbox[0].recipients, [self.user.email])
                self.assertEqual(outbox[0].body, "Test Body")
                self.assertEqual(len(outbox[0].attachments), 1)
                self.assertEqual(outbox[0].attachments[0].filename, 'test_attachment.txt')

        # Check if the temporary file was deleted after sending
        self.assertFalse(os.path.exists(temp_file_path))

    def test_send_wishlist_notifications(self):
        product_on_sale = Product(samplename='On Sale Item', price=100, onSale=1, onSalePrice=50, stock=10)
        product_back_in_stock = Product(samplename='Back in Stock Item', price=100, onSale=0, stock=10)
        self.session.add_all([product_on_sale, product_back_in_stock])
        self.session.commit()

        wishlist_item1 = Wishlist(user_id=self.user.id, product_id=product_on_sale.id)
        wishlist_item2 = Wishlist(user_id=self.user.id, product_id=product_back_in_stock.id)
        self.session.add_all([wishlist_item1, wishlist_item2])
        self.session.commit()

        with self.app.test_request_context():
            with self.mail.record_messages() as outbox:
                send_wishlist_notifications()

                self.assertEqual(len(outbox), 1)
                self.assertEqual(outbox[0].subject, "Wishlist Items Update")
                self.assertEqual(outbox[0].recipients, [self.user.email])
                self.assertIn("On Sale Item", outbox[0].body)
                self.assertIn("Back in Stock Item", outbox[0].body)

    def test_create_wishlist_message(self):
        on_sale_items = [Product(samplename='On Sale Item 1'), Product(samplename='On Sale Item 2')]
        back_in_stock_items = [Product(samplename='Back in Stock Item 1')]

        with self.app.test_request_context():
            message = create_wishlist_message(on_sale_items, back_in_stock_items)

        self.assertIn("The following wishlist items are now on sale:", message)
        self.assertIn("On Sale Item 1", message)
        self.assertIn("On Sale Item 2", message)
        self.assertIn("The following wishlist items are now back in stock:", message)
        self.assertIn("Back in Stock Item 1", message)

    def test_send_order_confirmation_email(self):
        with self.app.test_request_context():
            with self.mail.record_messages() as outbox:
                send_order_confirmation_email(self.user.email, "Test User")

                self.assertEqual(len(outbox), 1)
                self.assertEqual(outbox[0].subject, "Order Confirmation")
                self.assertEqual(outbox[0].recipients, [self.user.email])
                self.assertIn("Thank you for your purchase", outbox[0].body)


if __name__ == '__main__':
    unittest.main()
