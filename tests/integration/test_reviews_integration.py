import unittest

from flask import url_for
from flask_login import login_user

from modules.db.models import Review, ReportedReview, Purchase, PurchaseItem, Goods
from modules.reviews.utils import (
    get_review, has_purchased, has_already_reviewed
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
        self.admin = create_user(self, is_admin=True)
        self.goods = Goods(id=1, samplename='Test Product', price=1000)
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

        with self.app.test_request_context():
            login_user(self.user)
            response = self.client.post(url_for('reviews.report_review', review_id=review.id),
                                        data={'explanation': 'Inappropriate content'},
                                        follow_redirects=True)
            self.assertEqual(response.status_code, 200)

        reported_review = ReportedReview.query.filter_by(review_id=review.id).first()
        self.assertIsNotNone(reported_review)
        self.assertEqual(reported_review.user_id, self.user.id)
        self.assertEqual(reported_review.explanation, "Inappropriate content")

    def test_has_purchased_integration(self):
        purchase = Purchase(user_id=self.user.id, total_price=1000)
        self.session.add(purchase)
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
        purchase = Purchase(user_id=self.user.id, total_price=10.0)
        self.session.add(purchase)
        self.session.commit()

        purchase_item = PurchaseItem(purchase_id=purchase.id, goods_id=self.goods.id, quantity=1,
                                     price=self.goods.price)
        self.session.add(purchase_item)
        self.session.commit()

        with self.app.test_request_context():
            login_user(self.user)
            response = self.client.post(url_for('reviews.add_review'),
                                        data={
                                            'goods_id': self.goods.id,
                                            'rating': 5,
                                            'review': 'Excellent product!',
                                            'title': 'Great Buy',
                                            'pros': 'Durable, Affordable',
                                            'cons': 'None'},
                                        follow_redirects=True)
            self.assertEqual(response.status_code, 200)

        added_review = Review.query.filter_by(user_id=self.user.id, goods_id=self.goods.id).first()
        self.assertIsNotNone(added_review)
        self.assertEqual(added_review.rating, 5)
        self.assertEqual(added_review.review, 'Excellent product!')

    def test_reported_reviews_admin_view(self):
        review = Review(user_id=self.user.id, goods_id=self.goods.id, rating=5, review='Great!')
        self.session.add(review)
        self.session.commit()

        report = ReportedReview(review_id=review.id, user_id=self.user.id, explanation='Test report')
        self.session.add(report)
        self.session.commit()

        with self.app.test_request_context():
            login_user(self.admin)
            response = self.client.get(url_for('reviews.reported_reviews'))
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Test report', response.data)

    def test_reported_review_detail_admin_view(self):
        review = Review(user_id=self.user.id, goods_id=self.goods.id, rating=5, review='Great!')
        self.session.add(review)
        self.session.commit()

        report = ReportedReview(review_id=review.id, user_id=self.user.id, explanation='Test report')
        self.session.add(report)
        self.session.commit()

        with self.app.test_request_context():
            login_user(self.admin)
            response = self.client.get(url_for('reviews.reported_review_detail', review_id=review.id))
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Great!', response.data)
            self.assertIn(b'Test report', response.data)

    def test_leave_review_admin_action(self):
        review = Review(user_id=self.user.id, goods_id=self.goods.id, rating=5, review='Great!')
        self.session.add(review)
        self.session.commit()

        report = ReportedReview(review_id=review.id, user_id=self.user.id, explanation='Test report')
        self.session.add(report)
        self.session.commit()

        with self.app.test_request_context():
            login_user(self.admin)
            response = self.client.post(url_for('reviews.leave_review', review_id=review.id), follow_redirects=True)
            self.assertEqual(response.status_code, 200)

        # Check that the report is deleted but the review remains
        self.assertIsNone(ReportedReview.query.filter_by(review_id=review.id).first())
        self.assertIsNotNone(self.session.get(Review, review.id))

    def test_delete_review_admin_action(self):
        review = Review(user_id=self.user.id, goods_id=self.goods.id, rating=5, review='Great!')
        self.session.add(review)
        self.session.commit()

        report = ReportedReview(review_id=review.id, user_id=self.user.id, explanation='Test report')
        self.session.add(report)
        self.session.commit()

        with self.app.test_request_context():
            login_user(self.admin)
            response = self.client.post(url_for('reviews.delete_review', review_id=review.id), follow_redirects=True)
            self.assertEqual(response.status_code, 200)

        # Check that both the report and the review are deleted
        self.assertIsNone(ReportedReview.query.filter_by(review_id=review.id).first())
        self.assertIsNone(self.session.get(Review, review.id))

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
        with self.app.test_request_context():
            login_user(self.user)
            response = self.client.post(url_for('reviews.add_review'),
                                        data={
                                            'goods_id': self.goods.id,
                                            'rating': 5,
                                            'review': 'Great product!',
                                            'title': 'Excellent',
                                            'pros': 'Durable',
                                            'cons': 'None'},
                                        follow_redirects=True)
            self.assertEqual(response.status_code, 200)

        # Check if user has now reviewed
        self.assertTrue(has_already_reviewed(self.user.id, self.goods.id))

        # Get the review
        review = Review.query.filter_by(user_id=self.user.id, goods_id=self.goods.id).first()
        self.assertIsNotNone(review)

        # Report the review
        with self.app.test_request_context():
            login_user(self.user)
            response = self.client.post(url_for('reviews.report_review', review_id=review.id),
                                        data={'explanation': 'Test report'},
                                        follow_redirects=True)
            self.assertEqual(response.status_code, 200)

        reported_review = ReportedReview.query.filter_by(review_id=review.id).first()
        self.assertIsNotNone(reported_review)


if __name__ == '__main__':
    unittest.main()
