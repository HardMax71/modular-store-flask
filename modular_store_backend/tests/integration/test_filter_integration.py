import unittest
from datetime import datetime, timedelta

from flask_login import login_user

from modular_store_backend.modules.db.models import Product, Category, Tag, ProductPromotion, Review
from modular_store_backend.tests.base_test import BaseTest
from modular_store_backend.tests.util import create_user


class TestFilterViews(BaseTest):
    def setUp(self):
        super().setUp()
        self.user = create_user(self)
        self.category = Category(name='Test Category')
        self.tag = Tag(name='Test Tag')
        self.session.add_all([self.category, self.tag])
        self.session.commit()

    def create_product(self, name, price, category, tags=None, stock=10):
        product = Product(samplename=name, price=price,
                          category_id=category.id, stock=stock, description='Test Description')
        if tags:
            product.tags.extend(tags)
        self.session.add(product)
        self.session.commit()
        return product

    def create_review(self, product, rating):
        review = Review(product_id=product.id, user_id=self.user.id, rating=rating)
        self.session.add(review)
        self.session.commit()
        return review

    def test_filter_products(self):
        self.create_product('Test Product', 10.0, self.category, [self.tag])

        with self.app.test_request_context():
            with self.app.test_client():
                login_user(self.user)
                response = self.client.get('/filter', query_string={
                    'category_id': self.category.id,
                    'name_query': 'Test',
                    'sort_by': 'price_asc',
                    'tag_query': 'Test'
                })
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Test Product', response.data)

    def test_filter_by_category(self):
        self.create_product('Product 1', 10.0, self.category)
        category2 = Category(name='Another Category')
        self.session.add(category2)
        self.session.commit()
        self.create_product('Product 2', 20.0, category2)

        with self.app.test_request_context():
            with self.app.test_client():
                login_user(self.user)
                response = self.client.get('/filter', query_string={'category_id': self.category.id})
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Product 1', response.data)
                self.assertNotIn(b'Product 2', response.data)

    def test_filter_by_name(self):
        self.create_product('Unique Name', 10.0, self.category)
        self.create_product('Another Product', 20.0, self.category)

        with self.app.test_request_context():
            with self.app.test_client():
                login_user(self.user)
                response = self.client.get('/filter', query_string={'name_query': 'Unique'})
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Unique Name', response.data)
                self.assertNotIn(b'Another Product', response.data)

    def test_sort_by_price(self):
        self.create_product('Expensive Product', 100.0, self.category)
        self.create_product('Cheap Product', 10.0, self.category)

        with self.app.test_request_context():
            with self.app.test_client():
                login_user(self.user)
                response = self.client.get('/filter', query_string={'sort_by': 'price_asc'})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.data.index(b'Cheap Product') < response.data.index(b'Expensive Product'))

    def test_sort_by_rating(self):
        product1 = self.create_product('High Rated Product', 10.0, self.category)
        product2 = self.create_product('Low Rated Product', 20.0, self.category)
        self.create_review(product1, 5)
        self.create_review(product2, 2)

        with self.app.test_request_context():
            with self.app.test_client():
                login_user(self.user)
                response = self.client.get('/filter', query_string={'sort_by': 'rating'})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.data.index(b'High Rated Product') < response.data.index(b'Low Rated Product'))

    def test_filter_by_tag(self):
        tag1 = Tag(name='Tag1')
        tag2 = Tag(name='Tag2')
        self.session.add_all([tag1, tag2])
        self.session.commit()

        self.create_product('Product with Tag1', 10.0, self.category, [tag1])
        self.create_product('Product with Tag2', 20.0, self.category, [tag2])

        with self.app.test_request_context():
            with self.app.test_client():
                login_user(self.user)
                response = self.client.get('/filter', query_string={'tag_query': 'Tag1'})
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Product with Tag1', response.data)
                self.assertNotIn(b'Product with Tag2', response.data)

    def test_pagination(self):
        for i in range(25):  # Assuming PER_PAGE is less than 25
            self.create_product(f'Product {i}', 10.0, self.category)

        with self.app.test_request_context():
            with self.app.test_client():
                login_user(self.user)
                response = self.client.get('/filter', query_string={'page': 2})
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Product', response.data)  # Should contain some products
                self.assertNotIn(b'Product 0', response.data)  # First product should not be on second page

    def test_promoted_products(self):
        product = self.create_product('Promoted Product', 10.0, self.category)
        promotion = ProductPromotion(product_id=product.id,
                                     start_date=datetime.now() - timedelta(days=1),
                                     end_date=datetime.now() + timedelta(days=1),
                                     description='Test Promotion')
        self.session.add(promotion)
        self.session.commit()

        with self.app.test_request_context():
            with self.app.test_client():
                login_user(self.user)
                response = self.client.get('/filter')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Promoted Product', response.data)

    def test_out_of_stock_products(self):
        self.create_product('In Stock Product', 10.0, self.category, stock=10)
        self.create_product('Out of Stock Product', 20.0, self.category, stock=0)

        with self.app.test_request_context():
            with self.app.test_client():
                login_user(self.user)
                response = self.client.get('/filter')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'In Stock Product', response.data)
                self.assertNotIn(b'Out of Stock Product', response.data)

    def test_sort_options(self):
        from modular_store_backend.modules.filter.sort_options import SortOptions

        self.assertEqual(len(SortOptions.get_all()), 3)  # PRICE_ASC, PRICE_DESC, AVG_RATING_DESC
        self.assertIsNotNone(SortOptions.get_by_key('price_asc'))
        self.assertIsNone(SortOptions.get_by_key('invalid_key'))

    def test_apply_sort_option(self):
        from modular_store_backend.modules.filter.sort_options import SortOptions
        from modular_store_backend.modules.db.database import db

        product1 = self.create_product('Product 1', 10.0, self.category)
        product2 = self.create_product('Product 2', 20.0, self.category)
        self.create_review(product1, 4)
        self.create_review(product2, 5)

        query = db.session.query(Product)

        # Test price ascending
        sorted_query = SortOptions.PRICE_ASC.apply(query)
        results = sorted_query.all()
        self.assertEqual(results[0].samplename, 'Product 1')
        self.assertEqual(results[1].samplename, 'Product 2')

        # Test price descending
        sorted_query = SortOptions.PRICE_DESC.apply(query)
        results = sorted_query.all()
        self.assertEqual(results[0].samplename, 'Product 2')
        self.assertEqual(results[1].samplename, 'Product 1')

        # Test rating
        sorted_query = SortOptions.AVG_RATING_DESC.apply(query)
        results = sorted_query.all()
        self.assertEqual(results[0].samplename, 'Product 2')
        self.assertEqual(results[1].samplename, 'Product 1')


if __name__ == '__main__':
    unittest.main()
