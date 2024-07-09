import os
import unittest
from unittest.mock import patch, MagicMock
from typing import List

from config import AppConfig
from modules.db.models import Review, ReportedReview, Purchase, PurchaseItem, ReviewImage
from modules.reviews.utils import (
    get_review, report_review_in_db, has_purchased, has_already_reviewed,
    handle_uploaded_images, add_review_to_db
)
from tests.base_test import BaseTest


class TestReviewUtils(BaseTest):

    def setUp(self) -> None:
        super().setUp()
        # Create the required image files in the upload folder
        self.upload_folder = AppConfig.REVIEW_PICS_FOLDER
        os.makedirs(self.upload_folder, exist_ok=True)
        self.image_files = ['image1.jpg', 'image2.jpg']
        for image_file in self.image_files:
            open(os.path.join(self.upload_folder, image_file), 'a').close()

    def tearDown(self) -> None:
        super().tearDown()
        # Delete the image files and upload folder after the test
        for image_file in self.image_files:
            file_path = os.path.join(self.upload_folder, image_file)
            if os.path.exists(file_path):
                os.remove(file_path)

    def test_get_review(self) -> None:
        mock_review = Review(id=1, user_id=1, goods_id=1, rating=5)
        self.session.add(mock_review)
        self.session.commit()

        result = get_review(1)
        self.assertEqual(result, mock_review)

    def test_report_review_in_db(self) -> None:
        report_review_in_db(1, 1, "Test explanation")
        reported_review = ReportedReview.query.first()
        self.assertIsNotNone(reported_review)
        self.assertEqual(reported_review.review_id, 1)
        self.assertEqual(reported_review.user_id, 1)
        self.assertEqual(reported_review.explanation, "Test explanation")

    def test_has_purchased(self) -> None:
        purchase = Purchase(id=1, user_id=1, total_price=1000)
        purchase_item = PurchaseItem(purchase_id=1, goods_id=1, quantity=1, price=1000)
        self.session.add_all([purchase, purchase_item])
        self.session.commit()

        result = has_purchased(1, 1)
        self.assertTrue(result)

        result = has_purchased(1, 2)
        self.assertFalse(result)

    def test_has_already_reviewed(self) -> None:
        review = Review(user_id=1, goods_id=1, rating=5, review='Great!')
        self.session.add(review)
        self.session.commit()

        result = has_already_reviewed(1, 1)
        self.assertTrue(result)

        result = has_already_reviewed(1, 2)
        self.assertFalse(result)

    @patch('modules.reviews.utils.secure_filename')
    @patch('modules.reviews.utils.os.path.join')
    def test_handle_uploaded_images(self, mock_join: MagicMock, mock_secure_filename: MagicMock) -> None:
        mock_join.return_value = '/path/to/image.jpg'
        mock_secure_filename.return_value = 'image.jpg'

        mock_file1 = MagicMock()
        mock_file1.filename = 'image1.jpg'
        mock_file2 = MagicMock()
        mock_file2.filename = 'image2.jpg'

        result = handle_uploaded_images([mock_file1, mock_file2], '/upload/folder')
        self.assertEqual(result, ['image.jpg', 'image.jpg'])
        self.assertEqual(mock_file1.save.call_count, 1)
        self.assertEqual(mock_file2.save.call_count, 1)

    @patch('modules.reviews.utils.handle_uploaded_images')
    def test_add_review_to_db(self, mock_handle_uploaded_images: MagicMock) -> None:
        # Create actual image files
        image_paths = []
        for image_file in self.image_files:
            image_path = os.path.join(self.upload_folder, image_file)
            with open(image_path, 'wb') as f:
                f.write(b"Test image content")
            image_paths.append(image_path)

        # Mock the return value of handle_uploaded_images to return file names
        mock_handle_uploaded_images.return_value = ['image1.jpg', 'image2.jpg']

        review_data = {
            'user_id': 1,
            'goods_id': 1,
            'rating': 5,
            'review': 'Great product!',
            'title': 'Excellent',
            'pros': 'Durable',
            'cons': 'None'
        }

        add_review_to_db(review_data, image_paths)

        added_review = Review.query.first()
        self.assertIsNotNone(added_review)
        for key, value in review_data.items():
            self.assertEqual(getattr(added_review, key), value)

        review_images: List[ReviewImage] = ReviewImage.query.filter_by(review_id=added_review.id).all()
        self.assertEqual(len(review_images), 2)
        self.assertEqual(review_images[0]._image, 'image1.jpg')
        self.assertEqual(review_images[1]._image, 'image2.jpg')


if __name__ == '__main__':
    unittest.main()
