import random
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from flask import url_for
from flask_login import login_user

from modules.db.models import (
    Goods, Category, Ticket, RequestLog, Review,
    ShippingMethod,
    ReportedReview, Discount, Purchase
)
from tests.base_test import BaseTest
from tests.util import create_user


class TestAdminIntegration(BaseTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=True, define_load_user=True)

    def setUp(self):
        super().setUp()
        self.admin_user = create_user(self, is_admin=True)
        self.regular_user = create_user(self)
        self.product = Goods(samplename='Test Product', price=1000, stock=10)
        self.category = Category(name='Test Category')
        self.discount = Discount(code='TESTDISCOUNT', percentage=10, start_date=datetime.now().date(),
                                 end_date=(datetime.now() + timedelta(days=30)).date())
        self.session.add_all([self.product, self.category, self.discount])
        self.session.commit()

        self.purchase = Purchase(user_id=self.regular_user.id, total_price=random.randint(1000, 10000))
        self.session.add(self.purchase)
        self.session.commit()

    def login_admin(self):
        with self.app.test_request_context():
            login_user(self.admin_user)
            return self.client

    def test_admin_index_view(self):
        client = self.login_admin()
        response = client.get(url_for('admin.index'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Admin Dashboard', response.data)

    def test_user_view(self):
        client = self.login_admin()
        response = client.get(url_for('user.index_view'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Users Management', response.data)

    def test_goods_view(self):
        client = self.login_admin()
        response = client.get(url_for('goods.index_view'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.product.samplename.encode(), response.data)

    def test_category_view(self):
        client = self.login_admin()
        response = client.get(url_for('category.index_view'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.category.name.encode(), response.data)

    def test_purchase_view(self):
        client = self.login_admin()
        response = client.get(url_for('purchase.index_view'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(self.purchase.total_price).encode(), response.data)

    def test_review_view(self):
        client = self.login_admin()
        response = client.get(url_for('review.index_view'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Reviews Management', response.data)

    def test_wishlist_view(self):
        client = self.login_admin()
        response = client.get(url_for('wishlist.index_view'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Wishlists Management', response.data)

    def test_tag_view(self):
        client = self.login_admin()
        response = client.get(url_for('tag.index_view'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Tags Management', response.data)

    def test_product_promotion_view(self):
        client = self.login_admin()
        response = client.get(url_for('productpromotion.index_view'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Promotions', response.data)

    def test_discount_view(self):
        client = self.login_admin()
        response = client.get(url_for('discount.index_view'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.discount.code.encode(), response.data)

    def test_shipping_method_view(self):
        client = self.login_admin()
        response = client.get(url_for('shippingmethod.index_view'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Shipping Methods', response.data)

    def test_reported_review_view(self):
        client = self.login_admin()
        response = client.get(url_for('reportedreview.index_view'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Reported Reviews', response.data)

    def test_ticket_view(self):
        client = self.login_admin()
        response = client.get(url_for('ticket.index_view'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Tickets Management', response.data)

    def test_ticket_message_view(self):
        client = self.login_admin()
        response = client.get(url_for('ticketmessage.index_view'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Ticket Messages', response.data)

    def test_statistics_view(self):
        client = self.login_admin()
        response = client.get(url_for('statistics.index'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Statistics', response.data)

    def test_reports_view(self):
        client = self.login_admin()
        response = client.get(url_for('reports.index'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Reports', response.data)

    def test_analytics_view(self):
        client = self.login_admin()
        response = client.get(url_for('analytics.index'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Analytics', response.data)

    def test_assign_ticket(self):
        client = self.login_admin()
        ticket = Ticket(user_id=self.regular_user.id, title='Test Ticket', description='Test Description')
        self.session.add(ticket)
        self.session.commit()

        response = client.post(url_for('ticket.assign_ticket', ticket_id=ticket.id), data={
            'admin_id': self.admin_user.id
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Ticket assigned successfully', response.data)

    def test_generate_reports(self):
        client = self.login_admin()
        response = client.post(url_for('reports.index'), data={
            'tables': ['users', 'goods'],
            'file_format': 'csv'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')

    def test_analytics_data(self):
        # Create some request logs
        for _ in range(5):
            log = RequestLog(user_id=self.regular_user.id, ip_address='127.0.0.1',
                             endpoint='/test', method='GET', status_code=200,
                             execution_time=0.5, timestamp=datetime.now())
            self.session.add(log)
        self.session.commit()

        client = self.login_admin()
        response = client.post(url_for('analytics.index'), data={
            'start_date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
            'end_date': datetime.now().strftime('%Y-%m-%d')
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Total Requests: 5', response.data)

    def test_unauthorized_access(self):
        with self.app.test_request_context():
            with self.app.test_client() as client:
                login_user(self.regular_user)
                response = client.get(url_for('admin.index'))
                self.assertEqual(response.status_code, 302)  # Should redirect

    def test_create_user(self):
        client = self.login_admin()
        user: dict = {
            'username': 'newuser' + str(datetime.now().timestamp()),
            'email': 'newuser@example.com',
            'password': 'password123',
            'is_admin': False,
            'is_active': True
        }
        response = client.post(url_for('user.create_view'), data=user, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(user['username'].encode(), response.data)

    def test_edit_product(self):
        client = self.login_admin()
        product = {
            'samplename': 'Updated Product' + str(datetime.now().timestamp()),
            'price': random.randint(1000, 10000),
            'stock': random.randint(1, 100),
        }
        response = client.post(url_for('goods.edit_view', id=self.product.id),
                               data=product, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(product['samplename'].encode(), response.data)

    def test_delete_category(self):
        client = self.login_admin()
        response = client.post(url_for('category.delete_view', id=self.category.id), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.category.name.encode(), response.data)

    @patch('modules.admin.views.ProfileReport')
    def test_generate_statistics(self, mock_profile_report):
        mock_profile = MagicMock()
        mock_profile.to_html.return_value = '<html>Mock Profile Report</html>'
        mock_profile_report.return_value = mock_profile

        client = self.login_admin()
        response = client.post(url_for('statistics.index'), data={
            'tables': ['users', 'goods'],
            'data_percentage': 100
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/html')

    def test_create_discount(self):
        client = self.login_admin()
        discount_code = 'TESTDISCOUNT' + str(datetime.now().timestamp())
        response = client.post(url_for('discount.create_view'), data={
            'code': discount_code,
            'percentage': 10,
            'start_date': datetime.now().date(),
            'end_date': (datetime.now() + timedelta(days=30)).date()
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(discount_code.encode(), response.data)

    def test_edit_shipping_method(self):
        shipping_method = ShippingMethod(name='Standard', price=500)
        self.session.add(shipping_method)
        self.session.commit()

        client = self.login_admin()
        response = client.post(url_for('shippingmethod.edit_view', id=shipping_method.id), data={
            'name': 'Express',
            'price': 1000
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Express', response.data)

    def test_view_reported_review_details(self):
        review = Review(user_id=self.regular_user.id, goods_id=self.product.id, rating=5, review='Great product!')
        self.session.add(review)
        self.session.commit()

        reported_review = ReportedReview(review_id=review.id, user_id=self.admin_user.id,
                                         explanation='Suspicious review')
        self.session.add(reported_review)
        self.session.commit()

        client = self.login_admin()
        response = client.get(url_for('reviews.reported_review_detail', review_id=review.id))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Reported Review Detail', response.data)

    def test_create_product_promotion(self):
        client = self.login_admin()
        promotion_description = 'Special offer!' + str(datetime.now().timestamp())
        response = client.post(url_for('productpromotion.create_view'), data={
            'goods_id': self.product.id,
            'start_date': datetime.now().date(),
            'end_date': (datetime.now() + timedelta(days=7)).date(),
            'description': promotion_description
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(promotion_description.encode(), response.data)


if __name__ == '__main__':
    unittest.main()
