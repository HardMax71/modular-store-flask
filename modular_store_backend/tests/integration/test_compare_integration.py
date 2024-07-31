# /modular_store_backend/tests/integration/test_compare_integration.py
import json
import unittest

from flask import url_for
from flask_login import login_user

from modular_store_backend.modules.db.models import Product, ComparisonHistory
from modular_store_backend.tests.base_test import BaseTest
from modular_store_backend.tests.util import create_user


class TestCompareIntegration(BaseTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=True, define_load_user=True)

    def setUp(self):
        super().setUp()
        self.product1 = Product(samplename='Product 1', price=1000, stock=10)
        self.product2 = Product(samplename='Product 2', price=2000, stock=20)
        self.product3 = Product(samplename='Product 3', price=3000, stock=30)
        self.product4 = Product(samplename='product 4', price=4000, stock=40)
        self.session.add_all([self.product1, self.product2, self.product3, self.product4])
        self.session.commit()

        self.user = create_user(self)
        with self.app.test_request_context():
            with self.app.test_client():
                login_user(self.user)

    def test_compare_products_empty(self):
        response = self.client.get(url_for('compare.compare_products'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No Products to Compare', response.data)

    def test_compare_products_with_items(self):
        comparison = ComparisonHistory(user_id=self.user.id,
                                       product_ids=json.dumps([self.product1.id, self.product2.id]))
        self.session.add(comparison)
        self.session.commit()

        response = self.client.get(url_for('compare.compare_products'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product 1', response.data)
        self.assertIn(b'Product 2', response.data)

    def test_remove_from_comparison(self):
        comparison = ComparisonHistory(user_id=self.user.id,
                                       product_ids=json.dumps([self.product1.id, self.product2.id]))
        self.session.add(comparison)
        self.session.commit()

        response = self.client.post(url_for('compare.remove_from_comparison'), data={'product_id': self.product1.id},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product removed from comparison', response.data)

        updated_comparison = self.session.query(ComparisonHistory).filter_by(user_id=self.user.id).first()
        self.assertEqual(json.loads(updated_comparison.product_ids), [self.product2.id])

    def test_remove_from_comparison_not_in_list(self):
        comparison = ComparisonHistory(user_id=self.user.id, product_ids=json.dumps([self.product1.id]))
        self.session.add(comparison)
        self.session.commit()

        response = self.client.post(url_for('compare.remove_from_comparison'), data={'product_id': self.product2.id},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product is not in comparison', response.data)

    def test_add_to_comparison_new(self):
        response = self.client.post(url_for('compare.add_to_comparison'), data={'product_id': self.product1.id},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product added to comparison', response.data)

        comparison: ComparisonHistory = self.session.query(ComparisonHistory).filter_by(user_id=self.user.id).first()
        self.assertEqual(json.loads(comparison.product_ids), [self.product1.id])

    def test_add_to_comparison_existing(self):
        comparison = ComparisonHistory(user_id=self.user.id, product_ids=json.dumps([self.product1.id]))
        self.session.add(comparison)
        self.session.commit()

        response = self.client.post(url_for('compare.add_to_comparison'), data={'product_id': self.product2.id},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product added to comparison', response.data)

        updated_comparison = self.session.query(ComparisonHistory).filter_by(user_id=self.user.id).first()
        self.assertEqual(json.loads(updated_comparison.product_ids), [self.product1.id, self.product2.id])

    def test_add_to_comparison_limit_exceeded(self):
        comparison = ComparisonHistory(user_id=self.user.id,
                                       product_ids=json.dumps([self.product1.id, self.product2.id, self.product3.id]))
        self.session.add(comparison)
        self.session.commit()

        response = self.client.post(url_for('compare.add_to_comparison'), data={'product_id': 4},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'You can&#39;t compare so many products at a time.', response.data)

    def test_add_to_comparison_nonexistent_product(self):
        response = self.client.post(url_for('compare.add_to_comparison'), data={'product_id': 999},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product not found', response.data)

    def test_remove_from_comparison_last_product(self):
        comparison = ComparisonHistory(user_id=self.user.id, product_ids=json.dumps([self.product1.id]))
        self.session.add(comparison)
        self.session.commit()

        response = self.client.post(url_for('compare.remove_from_comparison'), data={'product_id': self.product1.id},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product removed from comparison', response.data)

        # Check that the ComparisonHistory entry has been deleted
        comparison_count = self.session.query(ComparisonHistory).filter_by(user_id=self.user.id).count()
        self.assertEqual(comparison_count, 0)

    def test_remove_from_comparison_no_comparison_history(self):
        response = self.client.post(url_for('compare.remove_from_comparison'), data={'product_id': self.product1.id},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No products in comparison', response.data)

    def test_add_to_comparison_product_already_in_list(self):
        comparison = ComparisonHistory(user_id=self.user.id, product_ids=json.dumps([self.product1.id]))
        self.session.add(comparison)
        self.session.commit()

        response = self.client.post(url_for('compare.add_to_comparison'), data={'product_id': self.product1.id},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product is already in comparison', response.data)

    def test_add_to_comparison_max_limit(self):
        # Set MAX_COMPARE_STOCK_THRESHOLD to 3 for this test
        self.app.config['MAX_COMPARE_STOCK_THRESHOLD'] = 3

        comparison = ComparisonHistory(user_id=self.user.id,
                                       product_ids=json.dumps([self.product1.id, self.product2.id, self.product3.id]))
        self.session.add(comparison)
        self.session.commit()

        response = self.client.post(url_for('compare.add_to_comparison'), data={'product_id': self.product4.id},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'You can&#39;t compare so many products at a time', response.data)

    def test_add_to_comparison_no_existing_comparison(self):
        response = self.client.post(url_for('compare.add_to_comparison'), data={'product_id': self.product1.id},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product added to comparison', response.data)

        comparison = self.session.query(ComparisonHistory).filter_by(user_id=self.user.id).first()
        self.assertIsNotNone(comparison)
        self.assertEqual(json.loads(comparison.product_ids), [self.product1.id])


if __name__ == '__main__':
    unittest.main()
