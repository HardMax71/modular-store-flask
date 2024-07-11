from unittest.mock import MagicMock

from flask_login import login_user

from modules.admin.views import _number_formatter, get_table_names
from modules.decorators import admin_required
from tests.base_test import BaseTest
from tests.util import create_user


class TestAdminUnit(BaseTest):
    def setUp(self):
        super().setUp()
        self.admin_user = create_user(self, is_admin=True)
        self.regular_user = create_user(self)

    def test_admin_required_decorator(self):
        @self.app.route('/test_admin_required')
        @admin_required()
        def test_route():
            return 'Admin access granted'

        with self.app.test_request_context():
            # Test with regular user
            login_user(self.regular_user)
            response = self.client.get('/test_admin_required')
            self.assertEqual(response.status_code, 302)  # Should redirect

            # Test with admin user
            login_user(self.admin_user)
            response = self.client.get('/test_admin_required')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'Admin access granted')

    def test_number_formatter(self):
        class MockView:
            pass

        mock_model = MagicMock()
        mock_model.test_attr = 123.456

        result = _number_formatter(MockView(), {}, mock_model, 'test_attr')
        self.assertEqual(result, '123.46')

    def test_get_table_names(self):
        table_names = get_table_names()
        expected_tables = ['users', 'goods', 'categories', 'purchases', 'reviews', 'wishlists', 'tags',
                           'product_promotions', 'discounts', 'shipping_methods', 'reported_reviews', 'tickets',
                           'ticket_messages']
        for table in expected_tables:
            self.assertIn(table, table_names)
