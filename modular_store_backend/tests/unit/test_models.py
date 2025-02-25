import unittest
from unittest.mock import patch, MagicMock

from modular_store_backend.modules.db.models import (
    User, Product, ProductImage, SocialAccount, ComparisonHistory,
    Purchase, PurchaseItem, ReportedReview, Review, ReviewImage,
    Address, Category, ShippingAddress, Wishlist, ProductSelectionOption,
    Discount, Notification, Tag, ProductPromotion, Ticket, TicketMessage
)
from modular_store_backend.tests.base_test import BaseTest
from werkzeug.security import generate_password_hash


class TestModelMethods(BaseTest):
    def setUp(self):
        super().setUp()
        # Fix: Add password that's required by DB constraint
        self.user = User(
            username='testuser',
            email='test@example.com',
            password=generate_password_hash('password123')
        )
        self.product = Product(samplename='Test Product', description='Test description')
        self.session.add_all([self.user, self.product])
        self.session.commit()

    def test_model_str_methods(self):
        # Test __str__ methods for various models without adding to DB
        self.assertEqual(str(self.user), 'testuser')
        self.assertEqual(str(self.product), f'{self.product.samplename}: {self.product.description[:20]}..')

        # Test other models without adding to DB
        social_account = SocialAccount(social_id='12345')
        self.assertEqual(str(social_account), '12345')

        notification = Notification(message='Test notification')
        self.assertEqual(str(notification), 'Test notification')

        tag = Tag(name='Test Tag')
        self.assertEqual(str(tag), 'Test Tag')

        discount = Discount(code='TEST10', percentage=10)
        self.assertEqual(str(discount), 'TEST10: 10%')

    @patch('modular_store_backend.modules.db.models.current_app')
    @patch('modular_store_backend.modules.db.models.os.path')
    def test_product_image_property(self, mock_path, mock_current_app):
        # Create a new test without accessing the database
        mock_current_app.config = {
            'PRODUCTS_PICS_FOLDER': '/test/products',
            'DEFAULT_PRODUCT_PIC': 'default.jpg'
        }

        # Create a ProductImage directly without accessing DB
        product_image = ProductImage(_image='image.jpg', product_id=1)

        # Test with existing file
        mock_path.exists.return_value = True
        mock_path.isfile.return_value = True
        mock_path.join.return_value = '/test/products/image.jpg'

        # Don't add to DB, just test the property
        self.assertEqual(product_image.image, 'image.jpg')

        # Test with non-existent file
        mock_path.exists.return_value = False
        self.assertEqual(product_image.image, 'default.jpg')

    @patch('modular_store_backend.modules.db.models.current_app')
    @patch('modular_store_backend.modules.db.models.os.path')
    def test_review_image_property(self, mock_path, mock_current_app):
        # Don't create a new session transaction
        self.session.remove()

        mock_current_app.config = {
            'REVIEW_PICS_FOLDER': '/test/reviews',
            'DEFAULT_REVIEW_PIC': 'default.jpg'
        }

        # Test with null image
        review_image = ReviewImage(_image=None, review_id=1)
        self.assertEqual(review_image.uploaded_image, 'default.jpg')

        # Test with existing file
        review_image._image = 'image.jpg'
        mock_path.exists.return_value = True
        mock_path.isfile.return_value = True
        mock_path.join.return_value = '/test/reviews/image.jpg'

        self.assertEqual(review_image.uploaded_image, 'image.jpg')