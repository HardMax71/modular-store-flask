import unittest
from datetime import datetime, timedelta

from flask import url_for
from flask_login import login_user

from modules.db.models import Goods, Category, Ticket, RequestLog
from tests.base_test import BaseTest
from tests.util import create_user


class TestAdminIntegration(BaseTest):
    # TODO: self.assertIn(b'List User', response.data) is not working
    #  since html page doesnt show 'List User' text => fix it

    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=True, define_load_user=True)

    def setUp(self):
        super().setUp()
        self.admin_user = create_user(self, is_admin=True)
        self.regular_user = create_user(self)
        self.product = Goods(samplename='Test Product', price=1000, stock=10)
        self.category = Category(name='Test Category')
        self.session.add_all([self.product, self.category])
        self.session.commit()

    def login_admin(self):
        with self.app.test_request_context():
            with self.app.test_client() as client:
                login_user(self.admin_user)
                return client

    def test_admin_index_view(self):
        client = self.login_admin()
        response = client.get(url_for('admin.index'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Admin Dashboard', response.data)

    def test_user_view(self):
        client = self.login_admin()
        response = client.get(url_for('user.index_view'))
        self.assertEqual(response.status_code, 200)
        # self.assertIn(b'List User', response.data)
        self.assertIn(b'admin/user/delete', response.data)

    def test_goods_view(self):
        client = self.login_admin()
        response = client.get(url_for('goods.index_view'))
        self.assertEqual(response.status_code, 200)
        # self.assertIn(b'List Goods', response.data)
        self.assertIn(b'admin/goods/delete', response.data)

    def test_category_view(self):
        client = self.login_admin()
        response = client.get(url_for('category.index_view'))
        self.assertEqual(response.status_code, 200)
        # self.assertIn(b'List Category', response.data)
        self.assertIn(b'admin/category/delete', response.data)

    def test_purchase_view(self):
        client = self.login_admin()
        response = client.get(url_for('purchase.index_view'))
        self.assertEqual(response.status_code, 200)
        # self.assertIn(b'List Purchase', response.data)
        self.assertIn(b'admin/purchase/delete', response.data)

    def test_review_view(self):
        client = self.login_admin()
        response = client.get(url_for('review.index_view'))
        self.assertEqual(response.status_code, 200)
        # self.assertIn(b'List Review', response.data)
        self.assertIn(b'admin/review/delete', response.data)

    def test_wishlist_view(self):
        client = self.login_admin()
        response = client.get(url_for('wishlist.index_view'))
        self.assertEqual(response.status_code, 200)
        # self.assertIn(b'List Wishlist', response.data)
        self.assertIn(b'admin/wishlist/delete', response.data)

    def test_tag_view(self):
        client = self.login_admin()
        response = client.get(url_for('tag.index_view'))
        self.assertEqual(response.status_code, 200)
        # self.assertIn(b'List Tag', response.data)
        self.assertIn(b'admin/tag/delete', response.data)

    def test_product_promotion_view(self):
        client = self.login_admin()
        response = client.get(url_for('productpromotion.index_view'))
        self.assertEqual(response.status_code, 200)
        # self.assertIn(b'List Product Promotion', response.data)
        self.assertIn(b'admin/productpromotion/?sort', response.data)

    def test_discount_view(self):
        client = self.login_admin()
        response = client.get(url_for('discount.index_view'))
        self.assertEqual(response.status_code, 200)
        # self.assertIn(b'List Discount', response.data)
        self.assertIn(b'admin/discount/delete', response.data)

    def test_shipping_method_view(self):
        client = self.login_admin()
        response = client.get(url_for('shippingmethod.index_view'))
        self.assertEqual(response.status_code, 200)
        # self.assertIn(b'List Shipping Method', response.data)
        self.assertIn(b'admin/shippingmethod/delete', response.data)

    def test_reported_review_view(self):
        client = self.login_admin()
        response = client.get(url_for('reportedreview.index_view'))
        self.assertEqual(response.status_code, 200)
        # self.assertIn(b'List Reported Review', response.data)
        self.assertIn(b'admin/reportedreview/delete', response.data)

    def test_ticket_view(self):
        client = self.login_admin()
        response = client.get(url_for('ticket.index_view'))
        self.assertEqual(response.status_code, 200)
        # self.assertIn(b'List Ticket', response.data)
        self.assertIn(b'admin/ticket/delete', response.data)

    def test_ticket_message_view(self):
        client = self.login_admin()
        response = client.get(url_for('ticketmessage.index_view'))
        self.assertEqual(response.status_code, 200)
        # self.assertIn(b'List Ticket Message', response.data)
        self.assertIn(b'admin/ticketmessage/delete', response.data)

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
        # TODO in reports.index value is with charset, here is returned w/out. Why?
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


if __name__ == '__main__':
    unittest.main()
