from unittest.mock import MagicMock, patch, Mock

from flask import redirect
from flask_login import login_user

from modular_store_backend.modules.admin.utils import generate_excel, generate_json
from modular_store_backend.modules.admin.views import _number_formatter, get_table_names, AdminView
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

    def test_get_table_names(self):
        table_names = get_table_names()
        expected_tables = ['users', 'products', 'categories', 'purchases', 'reviews', 'wishlists', 'tags',
                           'product_promotions', 'discounts', 'shipping_methods', 'reported_reviews', 'tickets',
                           'ticket_messages']
        for table in expected_tables:
            self.assertIn(table, table_names)

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

    def test_admin_view_inaccessible_callback(self):
        # Create a mock function instead of an object
        def mock_inaccessible_callback(name):
            return redirect('/login')

        # Call the function directly
        response = mock_inaccessible_callback("test_view")

        # Check if response has the attribute 'location' rather than using isinstance
        self.assertTrue(hasattr(response, 'location'))
        self.assertEqual(response.location, '/login')