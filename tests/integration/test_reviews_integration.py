import unittest

from modules.db.models import Review, ReportedReview, Purchase, PurchaseItem, Goods
from modules.reviews.utils import (
    get_review, report_review_in_db, has_purchased, has_already_reviewed,
    add_review_to_db
)
from tests.base_test import BaseTest
from tests.util import create_user


class TestReviewUtilsIntegration(BaseTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=True, define_load_user=True)

    def setUp(self):
        super().setUp()
        self.user = create_user(self)
        self.goods = Goods(id=1, samplename='Test Product', price=10.0)
        self.session.add(self.goods)
        self.session.commit()

    def test_get_review_integration(self):
        review = Review(user_id=self.user.id, goods_id=self.goods.id, rating=5, review='Great!')
        self.session.add(review)
        self.session.commit()

        retrieved_review = get_review(review.id)
        self.assertEqual(retrieved_review, review)

    def test_report_review_integration(self):
        review = Review(user_id=self.user.id, goods_id=self.goods.id, rating=5, review='Great!')
        self.session.add(review)
        self.session.commit()

        report_review_in_db(review.id, self.user.id, "Inappropriate content")

        reported_review = ReportedReview.query.filter_by(review_id=review.id).first()
        self.assertIsNotNone(reported_review)
        self.assertEqual(reported_review.user_id, self.user.id)
        self.assertEqual(reported_review.explanation, "Inappropriate content")

    def test_has_purchased_integration(self):
        purchase = Purchase(user_id=self.user.id, total_price=10.0)
        self.session.add(purchase)  # purchase item requires purchase.id to be set so creating purchase first
        self.session.commit()

        purchase_item = PurchaseItem(purchase_id=purchase.id, goods_id=self.goods.id, quantity=1,
                                     price=self.goods.price)
        self.session.add(purchase_item)
        self.session.commit()

        result = has_purchased(self.user.id, self.goods.id)
        self.assertTrue(result)

    def test_has_already_reviewed_integration(self):
        review = Review(user_id=self.user.id, goods_id=self.goods.id, rating=5, review='Great!')
        self.session.add(review)
        self.session.commit()

        result = has_already_reviewed(self.user.id, self.goods.id)
        self.assertTrue(result)

    def test_add_review_integration(self):
        review_data = {
            'user_id': self.user.id,
            'goods_id': self.goods.id,
            'rating': 5,
            'review': 'Excellent product!',
            'title': 'Great Buy',
            'pros': 'Durable, Affordable',
            'cons': 'None',
            'images': 'image1.jpg,image2.jpg'
        }
        add_review_to_db(review_data)

        added_review = Review.query.filter_by(user_id=self.user.id, goods_id=self.goods.id).first()
        self.assertIsNotNone(added_review)
        for key, value in review_data.items():
            self.assertEqual(getattr(added_review, key), value)

    def test_review_flow_integration(self):
        # Simulate a purchase
        purchase = Purchase(user_id=self.user.id, total_price=10.0)
        self.session.add(purchase)
        self.session.commit()

        purchase_item = PurchaseItem(purchase_id=purchase.id, goods_id=self.goods.id, quantity=1,
                                     price=self.goods.price)
        self.session.add(purchase_item)
        self.session.commit()

        # Check if user has purchased
        self.assertTrue(has_purchased(self.user.id, self.goods.id))

        # Check if user hasn't reviewed yet
        self.assertFalse(has_already_reviewed(self.user.id, self.goods.id))

        # Add a review
        review_data = {
            'user_id': self.user.id,
            'goods_id': self.goods.id,
            'rating': 5,
            'review': 'Great product!',
            'title': 'Excellent',
            'pros': 'Durable',
            'cons': 'None',
            'images': 'image1.jpg'
        }
        add_review_to_db(review_data)

        # Check if user has now reviewed
        self.assertTrue(has_already_reviewed(self.user.id, self.goods.id))

        # Get the review
        review = get_review(Review.query.filter_by(user_id=self.user.id, goods_id=self.goods.id).first().id)
        self.assertIsNotNone(review)

        # Report the review
        report_review_in_db(review.id, self.user.id, "Test report")
        reported_review = ReportedReview.query.filter_by(review_id=review.id).first()
        self.assertIsNotNone(reported_review)


if __name__ == '__main__':
    unittest.main()
