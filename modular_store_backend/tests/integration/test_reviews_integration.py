# /modular_store_backend/tests/integration/test_reviews_integration.py
import os
import unittest
from io import BytesIO

from werkzeug.datastructures import FileStorage

from modular_store_backend.modules.db.models import Review, ReportedReview, Purchase, PurchaseItem, Product, ReviewImage
from modular_store_backend.modules.reviews.utils import (
    get_review, report_review_with_explanation, has_purchased, has_already_reviewed,
    handle_uploaded_images, allowed_file, add_review_to_db
)
from modular_store_backend.tests.base_test import BaseTest
from modular_store_backend.tests.util import create_user


class TestReviewsIntegration(BaseTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=True, define_load_user=True)

    def setUp(self):
        super().setUp()
        self.user = create_user(self)
        self.admin = create_user(self, is_admin=True)
        self.product = Product(id=1, samplename='Test Product', price=1000)
        self.session.add(self.product)
        self.session.commit()

    def test_get_review(self):
        review = Review(user_id=self.user.id, product_id=self.product.id, rating=5, review='Great!')
        self.session.add(review)
        self.session.commit()

        retrieved_review = get_review(review.id)
        self.assertEqual(retrieved_review, review)

    def test_report_review_with_explanation(self):
        review = Review(user_id=self.user.id, product_id=self.product.id, rating=5, review='Great!')
        self.session.add(review)
        self.session.commit()

        report_review_with_explanation(review.id, self.user.id, 'Inappropriate content')

        reported_review = self.session.query(ReportedReview).filter_by(review_id=review.id).first()
        self.assertIsNotNone(reported_review)
        self.assertEqual(reported_review.user_id, self.user.id)
        self.assertEqual(reported_review.explanation, "Inappropriate content")

    def test_has_purchased(self):
        purchase = Purchase(user_id=self.user.id, total_price=1000)
        self.session.add(purchase)
        self.session.commit()

        purchase_item = PurchaseItem(purchase_id=purchase.id, product_id=self.product.id, quantity=1,
                                     price=self.product.price)
        self.session.add(purchase_item)
        self.session.commit()

        result = has_purchased(self.user.id, self.product.id)
        self.assertTrue(result)

    def test_has_already_reviewed(self):
        review = Review(user_id=self.user.id, product_id=self.product.id, rating=5, review='Great!')
        self.session.add(review)
        self.session.commit()

        result = has_already_reviewed(self.user.id, self.product.id)
        self.assertTrue(result)

    def test_handle_uploaded_images(self):
        test_image = FileStorage(
            stream=BytesIO(b'my file contents'),
            filename='test123.jpg',
            content_type='image/jpeg'
        )
        uploaded_files = [test_image]

        with self.app.test_request_context():
            upload_folder = self.app.config['REVIEW_PICS_FOLDER']
            result = handle_uploaded_images(uploaded_files, upload_folder)

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0] == 'test123.jpg')

        # Clean up the uploaded file
        os.remove(os.path.join(upload_folder, result[0]))

    def test_allowed_file(self):
        self.assertTrue(allowed_file('test.jpg'))
        self.assertTrue(allowed_file('test.png'))
        self.assertFalse(allowed_file('test.txt'))

    def test_add_review_to_db(self):
        review_data = {
            'user_id': self.user.id,
            'product_id': self.product.id,
            'rating': 5,
            'review': 'Excellent product!',
            'title': 'Great Buy',
            'pros': 'Durable, Affordable',
            'cons': 'None'
        }
        test_image = FileStorage(
            stream=BytesIO(b'my file contents'),
            filename='test.jpg',
            content_type='image/jpeg'
        )

        with self.app.test_request_context():
            add_review_to_db(review_data, [test_image])

        added_review = self.session.query(Review).filter_by(user_id=self.user.id, product_id=self.product.id).first()
        self.assertIsNotNone(added_review)
        self.assertEqual(added_review.rating, 5)
        self.assertEqual(added_review.review, 'Excellent product!')

        review_image = self.session.query(ReviewImage).filter_by(review_id=added_review.id).first()
        self.assertIsNotNone(review_image)
        print(review_image._image)
        self.assertTrue(review_image._image == 'test.jpg')

        # Clean up the uploaded file
        os.remove(os.path.join(self.app.config['REVIEW_PICS_FOLDER'], review_image._image))

    def test_review_flow_integration(self):
        # Simulate a purchase
        purchase = Purchase(user_id=self.user.id, total_price=1000)
        self.session.add(purchase)
        self.session.commit()

        purchase_item = PurchaseItem(purchase_id=purchase.id, product_id=self.product.id, quantity=1,
                                     price=self.product.price)
        self.session.add(purchase_item)
        self.session.commit()

        # Check if user has purchased
        self.assertTrue(has_purchased(self.user.id, self.product.id))

        # Check if user hasn't reviewed yet
        self.assertFalse(has_already_reviewed(self.user.id, self.product.id))

        # Add a review
        review_data = {
            'user_id': self.user.id,
            'product_id': self.product.id,
            'rating': 5,
            'review': 'Great product!',
            'title': 'Excellent',
            'pros': 'Durable',
            'cons': 'None'
        }
        test_image = FileStorage(
            stream=BytesIO(b'my file contents'),
            filename='test.jpg',
            content_type='image/jpeg'
        )

        with self.app.test_request_context():
            add_review_to_db(review_data, [test_image])

        # Check if user has now reviewed
        self.assertTrue(has_already_reviewed(self.user.id, self.product.id))

        # Get the review
        review = self.session.query(Review).filter_by(user_id=self.user.id, product_id=self.product.id).first()
        self.assertIsNotNone(review)

        # Report the review
        report_review_with_explanation(review.id, self.user.id, 'Test report')

        reported_review = self.session.query(ReportedReview).filter_by(review_id=review.id).first()
        self.assertIsNotNone(reported_review)

        # Clean up the uploaded file
        review_image = self.session.query(ReviewImage).filter_by(review_id=review.id).first()
        if review_image:
            os.remove(os.path.join(self.app.config['REVIEW_PICS_FOLDER'], review_image._image))


if __name__ == '__main__':
    unittest.main()
