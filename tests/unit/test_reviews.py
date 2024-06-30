import unittest
from unittest.mock import patch, MagicMock

from modules.db.models import Review, ReportedReview, Purchase, PurchaseItem
from modules.reviews.utils import (
    get_review, report_review_in_db, has_purchased, has_already_reviewed,
    handle_uploaded_images, add_review_to_db
)
from tests.base_test import BaseTest


class TestReviewUtils(BaseTest):

    def test_get_review(self):
        mock_review = Review(id=1, user_id=1, goods_id=1, rating=5)
        self.session.add(mock_review)
        self.session.commit()

        result = get_review(1)
        self.assertEqual(result, mock_review)

    def test_report_review_in_db(self):
        report_review_in_db(1, 1, "Test explanation")
        reported_review = ReportedReview.query.first()
        self.assertIsNotNone(reported_review)
        self.assertEqual(reported_review.review_id, 1)
        self.assertEqual(reported_review.user_id, 1)
        self.assertEqual(reported_review.explanation, "Test explanation")

    def test_has_purchased(self):
        purchase = Purchase(id=1, user_id=1, total_price=10.0)
        purchase_item = PurchaseItem(purchase_id=1, goods_id=1, quantity=1, price=10.0)
        self.session.add_all([purchase, purchase_item])
        self.session.commit()

        result = has_purchased(1, 1)
        self.assertTrue(result)

        result = has_purchased(1, 2)
        self.assertFalse(result)

    def test_has_already_reviewed(self):
        review = Review(user_id=1, goods_id=1, rating=5, review='Great!')
        self.session.add(review)
        self.session.commit()

        result = has_already_reviewed(1, 1)
        self.assertTrue(result)

        result = has_already_reviewed(1, 2)
        self.assertFalse(result)

    @patch('modules.reviews.utils.secure_filename')
    @patch('modules.reviews.utils.os.path.join')
    def test_handle_uploaded_images(self, mock_join, mock_secure_filename):
        mock_join.return_value = '/path/to/image.jpg'
        mock_secure_filename.return_value = 'image.jpg'

        mock_file1 = MagicMock()
        mock_file1.filename = 'image1.jpg'
        mock_file2 = MagicMock()
        mock_file2.filename = 'image2.jpg'

        result = handle_uploaded_images([mock_file1, mock_file2], '/upload/folder')
        self.assertEqual(result, 'image.jpg,image.jpg')
        self.assertEqual(mock_file1.save.call_count, 1)
        self.assertEqual(mock_file2.save.call_count, 1)

    def test_add_review_to_db(self):
        review_data = {
            'user_id': 1,
            'goods_id': 1,
            'rating': 5,
            'review': 'Great product!',
            'title': 'Excellent',
            'pros': 'Durable',
            'cons': 'None',
            'images': 'image1.jpg,image2.jpg'
        }
        add_review_to_db(review_data)

        added_review = Review.query.first()
        self.assertIsNotNone(added_review)
        for key, value in review_data.items():
            self.assertEqual(getattr(added_review, key), value)


if __name__ == '__main__':
    unittest.main()
