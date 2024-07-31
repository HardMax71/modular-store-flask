# /modular_store_backend/tests/unit/test_admin.py
import unittest
from unittest.mock import MagicMock, patch

from flask_login import login_user

from modular_store_backend.modules.admin.utils import generate_csv, generate_excel, generate_json
from modular_store_backend.modules.admin.views import _number_formatter, get_table_names
from modular_store_backend.modules.decorators import admin_required
from modular_store_backend.tests.base_test import BaseTest
from modular_store_backend.tests.util import create_user


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

    @patch('sqlalchemy.inspect')
    def test_get_table_names(self, mock_inspect):
        mock_inspect().get_table_names.return_value = [
            'addresses', 'cart', 'categories', 'comparison_history', 'discounts', 'notifications',
            'product_images', 'product_promotions', 'product_selection_option', 'products', 'products_tags',
            'purchase_items', 'purchases', 'recently_viewed_products', 'related_products', 'reported_reviews',
            'request_logs', 'review_images', 'reviews', 'shipping_addresses', 'shipping_methods',
            'social_accounts', 'tags', 'ticket_messages', 'tickets', 'user_discounts', 'user_preferences',
            'users', 'wishlists'
        ]

        table_names = get_table_names()
        expected_tables = [
            'addresses', 'cart', 'categories', 'comparison_history', 'discounts', 'notifications',
            'product_images', 'product_promotions', 'product_selection_option', 'products', 'products_tags',
            'purchase_items', 'purchases', 'recently_viewed_products', 'related_products', 'reported_reviews',
            'request_logs', 'review_images', 'reviews', 'shipping_addresses', 'shipping_methods',
            'social_accounts', 'tags', 'ticket_messages', 'tickets', 'user_discounts', 'user_preferences',
            'users', 'wishlists'
        ]
        self.assertEqual(table_names, expected_tables)

    @patch('modular_store_backend.modules.admin.utils.send_file')
    def test_generate_csv(self, mock_send_file):
        data = {
            "table1": [
                {"column1": "value1", "column2": "value2"},
                {"column1": "value3", "column2": "value4"}
            ]
        }
        generate_csv(data)
        self.assertTrue(mock_send_file.called)
        args, kwargs = mock_send_file.call_args
        self.assertIn('data.csv', kwargs['download_name'])

    @patch('modular_store_backend.modules.admin.utils.send_file')
    def test_generate_excel(self, mock_send_file):
        data = {
            "table1": [
                {"column1": "value1", "column2": "value2"},
                {"column1": "value3", "column2": "value4"}
            ]
        }
        generate_excel(data)
        self.assertTrue(mock_send_file.called)
        args, kwargs = mock_send_file.call_args
        self.assertIn('data.xlsx', kwargs['download_name'])

    @patch('modular_store_backend.modules.admin.utils.send_file')
    def test_generate_json(self, mock_send_file):
        data = {
            "table1": [
                {"column1": "value1", "column2": "value2"},
                {"column1": "value3", "column2": "value4"}
            ]
        }
        generate_json(data)
        self.assertTrue(mock_send_file.called)
        args, kwargs = mock_send_file.call_args
        self.assertIn('data.json', kwargs['download_name'])


if __name__ == '__main__':
    unittest.main()
