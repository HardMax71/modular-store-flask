import unittest
from datetime import datetime, timedelta

from flask_login import login_user

from modules.db.database import db, Base
from modules.db.models import Goods, Category, Tag, ProductPromotion
from tests.base_integration_test import BaseIntegrationTest
from tests.util import create_user


class TestFilterViews(BaseIntegrationTest):
    def setUp(self):
        super().setUp()
        self.user = create_user(self)
        self.category = Category(name='Test Category')
        self.tag = Tag(name='Test Tag')
        db.session.add_all([self.category, self.tag])
        db.session.commit()

    def tearDown(self):
        super().tearDown()
        db.session.remove()
        Base.metadata.drop_all(bind=db.engine)
        Base.metadata.create_all(bind=db.engine)

    def create_product(self, name, price, category, tags=None, stock=10):
        product = Goods(samplename=name, price=price,
                        category_id=category.id, stock=stock, description='Test Description')
        if tags:
            product.tags.extend(tags)
        db.session.add(product)
        db.session.commit()
        return product

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
        db.session.add(category2)
        db.session.commit()
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

    def test_filter_by_tag(self):
        tag1 = Tag(name='Tag1')
        tag2 = Tag(name='Tag2')
        db.session.add_all([tag1, tag2])
        db.session.commit()

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
        promotion = ProductPromotion(goods_id=product.id,
                                     start_date=datetime.now() - timedelta(days=1),
                                     end_date=datetime.now() + timedelta(days=1),
                                     description='Test Promotion')
        db.session.add(promotion)
        db.session.commit()

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


if __name__ == '__main__':
    unittest.main()
