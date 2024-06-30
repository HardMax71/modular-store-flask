import json
import unittest

from flask import url_for
from flask_login import login_user

from modules.db.models import Goods, Category, Review, RecentlyViewedProduct, ComparisonHistory, Variant
from tests.base_test import BaseTest
from tests.util import create_user


class TestMainIntegration(BaseTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=True, define_load_user=True)

    def setUp(self):
        super().setUp()
        self.category = Category(name='Test Category')
        self.goods = Goods(samplename='Test Product', price=10.0, category=self.category, stock=10)
        self.session.add_all([self.category, self.goods])
        self.session.commit()

        self.user = create_user(self)
        with self.app.test_request_context():
            with self.app.test_client():
                login_user(self.user)

    def test_index_route(self):
        response = self.client.get(url_for('main.index'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Product', response.data)

    def test_search_route(self):
        response = self.client.get(url_for('main.search_route', query='Test'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Product', response.data)

    def test_goods_page_route(self):
        response = self.client.get(url_for('main.goods_page', id=self.goods.id))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Product', response.data)

    def test_toggle_wishlist_route(self):
        response = self.client.post(url_for('main.toggle_wishlist'), data={'goods_id': self.goods.id},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product added to your wishlist!', response.data)

        # Toggle again to remove
        response = self.client.post(url_for('main.toggle_wishlist'), data={'goods_id': self.goods.id},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product removed from your wishlist.', response.data)

    def test_recommendations_route(self):
        response = self.client.get(url_for('main.recommendations'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Recommendations', response.data)

    def test_apply_discount_route(self):
        response = self.client.post(url_for('main.apply_discount'), data={'discount_code': 'INVALID'},
                                    follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid discount code.', response.data)

    def test_terms_route(self):
        response = self.client.get(url_for('main.terms'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Terms of Usage', response.data)

    def test_return_policy_route(self):
        response = self.client.get(url_for('main.return_policy'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Return Policy', response.data)

    def test_contact_us_route(self):
        response = self.client.get(url_for('main.contact_us'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Contact Us', response.data)

    def test_faq_route(self):
        response = self.client.get(url_for('main.faq'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'FAQ', response.data)

    def test_robots_txt_route(self):
        response = self.client.get(url_for('main.robots'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'User-agent', response.data)

    def test_goods_page_with_reviews(self):
        review = Review(user_id=self.user.id, goods_id=self.goods.id, rating=5, review='Great product!')
        self.session.add(review)
        self.session.commit()

        response = self.client.get(url_for('main.goods_page', id=self.goods.id))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Great product!', response.data)

    def test_goods_page_with_variants(self):
        variant = Variant(goods_id=self.goods.id, name='Size', value='Large')
        self.session.add(variant)
        self.session.commit()

        response = self.client.get(url_for('main.goods_page', id=self.goods.id))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Size', response.data)
        self.assertIn(b'Large', response.data)

    def test_goods_page_with_comparison(self):
        comparison = ComparisonHistory(user_id=self.user.id, product_ids=json.dumps([self.goods.id]))
        self.session.add(comparison)
        self.session.commit()

        response = self.client.get(url_for('main.goods_page', id=self.goods.id))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'remove-from-comparison', response.data)  # part of class name of button responsible for deleting

    def test_recently_viewed_products(self):
        self.client.get(url_for('main.goods_page', id=self.goods.id))

        recently_viewed = RecentlyViewedProduct.query.filter_by(user_id=self.user.id,
                                                                goods_id=self.goods.id).first()
        self.assertIsNotNone(recently_viewed)

    def test_pagination(self):
        # Add more products to test pagination
        for i in range(20):
            product = Goods(samplename=f'Product {i}', price=10.0, category=self.category, stock=10)
            self.session.add(product)
        self.session.commit()

        response = self.client.get(url_for('main.index', page=2))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Product', response.data)
        self.assertIn(b'Next', response.data)

    def test_search_no_results(self):
        response = self.client.get(url_for('main.search_route', query='NonexistentProduct'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No products found', response.data)

    def test_goods_page_nonexistent_product(self):
        response = self.client.get(url_for('main.goods_page', id=9999))
        self.assertEqual(response.status_code, 302)  # Redirect to index
        self.assertIn('Product not found', self.get_flashed_messages(with_categories=True)[0][1])

    def test_toggle_wishlist_nonexistent_product(self):
        response = self.client.post(url_for('main.toggle_wishlist'), data={'goods_id': 9999}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid product ID', response.data)

    def get_flashed_messages(self, with_categories=False):
        with self.client.session_transaction() as session:
            return session.get('_flashes', [])


if __name__ == '__main__':
    unittest.main()
