import random
import unittest

from flask import url_for
from flask_login import LoginManager
from flask_login import login_user
from werkzeug.security import generate_password_hash

from app import create_app
from config import AppConfig
from modules.db.database import db
from modules.db.models import Address, Notification
from modules.db.models import User


class TestProfileRoutes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        AppConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        cls.app = create_app(AppConfig)
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False

        cls.app_context = cls.app.app_context()
        cls.app_context.push()

        LoginManager().init_app(cls.app)

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.engine.dispose()
        cls.app_context.pop()

    def setUp(self):
        self.client = self.app.test_client()
        self.session = db.session
        self.session.begin()

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def create_user(self, username: str = None, email: str = None, password: str = None):
        if username is None:
            username = f'user_{random.randint(0, 123456)}'
        if email is None:
            email = f'{random.randint(0, 123456)}@example.com'
        if password is None:
            password = f'password_{random.randint(0, 123456)}'

        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed_password)
        self.session.add(user)
        self.session.commit()
        return user

    def test_profile_info_route(self):
        user = self.create_user()
        with self.app.test_request_context():
            login_user(user)
            response = self.client.get(url_for('profile.profile_info'))
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Profile', response.data)

    def test_notifications_route(self):
        user = self.create_user()
        notification = Notification(user_id=user.id, message='Test notification')
        self.session.add(notification)
        self.session.commit()

        with self.app.test_request_context():
            login_user(user)
            response = self.client.get(url_for('profile.notifications'))
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Test notification', response.data)

    def test_mark_notification_as_read(self):
        user = self.create_user()
        notification = Notification(user_id=user.id, message='Test notification', read=False)
        self.session.add(notification)
        self.session.commit()

        with self.app.test_request_context():
            login_user(user)
            response = self.client.post(url_for('profile.mark_notification_as_read', notification_id=notification.id))
            self.assertEqual(response.status_code, 302)
            updated_notification = self.session.get(Notification, notification.id)
            self.assertTrue(updated_notification.read)

    def test_add_address_route(self):
        user = self.create_user()
        with self.app.test_request_context():
            login_user(user)
            response = self.client.post(url_for('profile.add_address'), data={
                'address_line1': '123 Test St',
                'city': 'Test City',
                'state': 'Test State',
                'zip_code': '12345',
                'country': 'Test Country'
            })
            self.assertEqual(response.status_code, 302)
            address = self.session.query(Address).filter_by(user_id=user.id).first()
            self.assertIsNotNone(address)
            self.assertEqual(address.address_line1, '123 Test St')

    def test_edit_address_route(self):
        user = self.create_user()
        address = Address(user_id=user.id, address_line1='123 Old St', city='Old City', state='Old State',
                          zip_code='54321', country='Old Country')
        self.session.add(address)
        self.session.commit()

        with self.app.test_request_context():
            login_user(user)
            response = self.client.post(url_for('profile.edit_address', address_id=address.id), data={
                'address_line1': '456 New St',
                'address_line2': 'New Line 2',
                'city': 'New City',
                'state': 'New State',
                'zip_code': '67890',
                'country': 'New Country'
            })
            self.assertEqual(response.status_code, 302)
            self.session.refresh(address)
            self.assertEqual(address.address_line1, '456 New St')
            self.assertEqual(address.city, 'New City')

    def test_delete_address_route(self):
        user = self.create_user()
        address = Address(user_id=user.id, address_line1='123 Delete St', city='Delete City', state='Delete State',
                          zip_code='12345', country='Delete Country')
        self.session.add(address)
        self.session.commit()

        with self.app.test_request_context():
            login_user(user)
            response = self.client.post(url_for('profile.delete_address', address_id=address.id))
            self.assertEqual(response.status_code, 302)
            address = self.session.query(Address).filter_by(id=address.id).first()
            self.assertIsNone(address)


if __name__ == '__main__':
    unittest.main()
