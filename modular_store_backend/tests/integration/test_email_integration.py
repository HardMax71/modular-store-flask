import unittest

from flask_login import login_user
from flask_mail import Mail

from modular_store_backend.modules.db.models import Product, Wishlist
from modular_store_backend.modules.email import send_email, send_wishlist_notifications, send_order_confirmation_email
from modular_store_backend.tests.base_test import BaseTest
from modular_store_backend.tests.util import create_user


class TestEmailFunctionsIntegration(BaseTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=True,
                           define_load_user=True)

        cls.mail = Mail(cls.app)

    def test_send_email(self):
        with self.app.test_request_context():
            user = create_user(self)
            login_user(user)

            with self.app.app_context():
                with self.mail.record_messages() as outbox:
                    send_email(user.email, "Test Subject", "Test Body")

                    self.assertEqual(len(outbox), 1)
                    self.assertEqual(outbox[0].subject, "Test Subject")
                    self.assertEqual(outbox[0].recipients, [user.email])
                    self.assertEqual(outbox[0].body, "Test Body")

    def test_send_wishlist_notifications(self):
        with self.app.test_request_context():
            user = create_user(self)

            product_on_sale = Product(samplename='On Sale Item', price=100, onSale=1, onSalePrice=50, stock=10)
            product_back_in_stock = Product(samplename='Back in Stock Item', price=100, onSale=0, stock=10)
            self.session.add_all([product_on_sale, product_back_in_stock])
            self.session.commit()

            wishlist_item1 = Wishlist(user_id=user.id, product_id=product_on_sale.id)
            wishlist_item2 = Wishlist(user_id=user.id, product_id=product_back_in_stock.id)
            self.session.add_all([wishlist_item1, wishlist_item2])
            self.session.commit()

            login_user(user)

            with self.app.app_context():
                with self.mail.record_messages() as outbox:
                    send_wishlist_notifications()

                    self.assertEqual(len(outbox), 1)
                    self.assertEqual(outbox[0].subject, "Wishlist Items Update")
                    self.assertEqual(outbox[0].recipients, [user.email])
                    self.assertIn("On Sale Item", outbox[0].body)
                    self.assertIn("Back in Stock Item", outbox[0].body)

    def test_send_order_confirmation_email(self):
        with self.app.test_request_context():
            user = create_user(self)
            self.session.add(user)
            self.session.commit()

            login_user(user)

            with self.app.app_context():
                with self.mail.record_messages() as outbox:
                    send_order_confirmation_email(user.email, "Test User")

                    self.assertEqual(len(outbox), 1)
                    self.assertEqual(outbox[0].subject, "Order Confirmation")
                    self.assertEqual(outbox[0].recipients, [user.email])
                    self.assertIn("Thank you for your purchase", outbox[0].body)


if __name__ == '__main__':
    unittest.main()
