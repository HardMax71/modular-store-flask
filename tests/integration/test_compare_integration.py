import json
import unittest

from flask import url_for
from flask_login import login_user

from modules.db.models import Goods, ComparisonHistory
from tests.base_test import BaseTest
from tests.util import create_user


class TestCompareIntegration(BaseTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=True, define_load_user=True)

    def setUp(self):
        super().setUp()
        self.product1 = Goods(samplename='Product 1', price=1000, stock=10)
        self.product2 = Goods(samplename='Product 2', price=2000, stock=20)
        self.product3 = Goods(samplename='Product 3', price=3000, stock=30)
        self.product4 = Goods(samplename='product 4', price=4000, stock=40)
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

        response = self.client.post(url_for('compare.remove_from_comparison'), data={'goods_id': self.product1.id},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product removed from comparison', response.data)

        updated_comparison = ComparisonHistory.query.filter_by(user_id=self.user.id).first()
        self.assertEqual(json.loads(updated_comparison.product_ids), [self.product2.id])

    def test_remove_from_comparison_not_in_list(self):
        comparison = ComparisonHistory(user_id=self.user.id, product_ids=json.dumps([self.product1.id]))
        self.session.add(comparison)
        self.session.commit()

        response = self.client.post(url_for('compare.remove_from_comparison'), data={'goods_id': self.product2.id},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product is not in comparison', response.data)

    def test_add_to_comparison_new(self):
        response = self.client.post(url_for('compare.add_to_comparison'), data={'goods_id': self.product1.id},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product added to comparison', response.data)

        comparison = ComparisonHistory.query.filter_by(user_id=self.user.id).first()
        self.assertEqual(json.loads(comparison.product_ids), [self.product1.id])

    def test_add_to_comparison_existing(self):
        comparison = ComparisonHistory(user_id=self.user.id, product_ids=json.dumps([self.product1.id]))
        self.session.add(comparison)
        self.session.commit()

        response = self.client.post(url_for('compare.add_to_comparison'), data={'goods_id': self.product2.id},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product added to comparison', response.data)

        updated_comparison = ComparisonHistory.query.filter_by(user_id=self.user.id).first()
        self.assertEqual(json.loads(updated_comparison.product_ids), [self.product1.id, self.product2.id])

    def test_add_to_comparison_limit_exceeded(self):
        comparison = ComparisonHistory(user_id=self.user.id,
                                       product_ids=json.dumps([self.product1.id, self.product2.id, self.product3.id]))
        self.session.add(comparison)
        self.session.commit()

        response = self.client.post(url_for('compare.add_to_comparison'), data={'goods_id': 4},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'You can only compare up to 3 products at a time', response.data)

    def test_add_to_comparison_nonexistent_product(self):
        response = self.client.post(url_for('compare.add_to_comparison'), data={'goods_id': 999},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product not found', response.data)


if __name__ == '__main__':
    unittest.main()
