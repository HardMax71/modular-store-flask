import unittest

from flask_login import login_user

from modules.db.database import db
from modules.db.models import Ticket
from tests.base_integration_test import BaseIntegrationTest
from tests.util import create_user


class TestTicketsViews(BaseIntegrationTest):
    def test_create_ticket(self):
        user = create_user(self)
        with self.app.test_request_context():
            with self.app.test_client():
                login_user(user)
                response = self.client.post('/tickets/create', data={
                    'title': 'Test Ticket',
                    'description': 'Test Description',
                    'priority': 'high'
                })
                self.assertEqual(response.status_code, 302)

    def test_list_tickets(self):
        user = create_user(self)
        with self.app.test_request_context():
            with self.app.test_client():
                login_user(user)
                ticket = Ticket(user_id=user.id, title='Test Ticket', description='Test Description')
                db.session.add(ticket)
                db.session.commit()

                response = self.client.get('/tickets/')
                self.assertEqual(response.status_code, 200)

    def test_update_ticket(self):
        admin_user = create_user(self, is_admin=True)
        with self.app.test_request_context():
            with self.app.test_client():
                login_user(admin_user)
                ticket = Ticket(user_id=admin_user.id, title='Old Title', description='Old Description')
                db.session.add(ticket)
                db.session.commit()

                response = self.client.post(f'/tickets/{ticket.id}/update', data={
                    'status': 'closed',
                    'priority': 'low',
                    'title': 'New Title',
                    'description': 'New Description'
                })
                self.assertEqual(response.status_code, 302)

    def test_ticket_details(self):
        user = create_user(self)
        with self.app.test_request_context():
            with self.app.test_client():
                login_user(user)
                ticket = Ticket(user_id=user.id, title='Test Ticket', description='Test Description')
                db.session.add(ticket)
                db.session.commit()

                response = self.client.get(f'/tickets/{ticket.id}')
                self.assertEqual(response.status_code, 200)

    def test_add_message_to_ticket(self):
        user = create_user(self)
        with self.app.test_request_context():
            with self.app.test_client():
                login_user(user)
                ticket = Ticket(user_id=user.id, title='Test Ticket', description='Test Description')
                db.session.add(ticket)
                db.session.commit()

                response = self.client.post(f'/tickets/{ticket.id}', data={
                    'message': 'Test Message'
                })
                self.assertEqual(response.status_code, 200)

    def test_unauthorized_access(self):
        user = create_user(self)
        other_user = create_user(self)
        with self.app.test_request_context():
            with self.app.test_client():
                login_user(other_user)
                ticket = Ticket(user_id=user.id, title='Test Ticket', description='Test Description')
                db.session.add(ticket)
                db.session.commit()

                response = self.client.get(f'/tickets/{ticket.id}')
                self.assertEqual(response.status_code, 302)  # Redirected due to lack of permission

    def test_admin_access(self):
        user = create_user(self)
        admin_user = create_user(self, is_admin=True)
        with self.app.test_request_context():
            with self.app.test_client():
                login_user(admin_user)

                ticket = Ticket(user_id=user.id, title='Test Ticket', description='Test Description')
                db.session.add(ticket)
                db.session.commit()

                response = self.client.get(f'/tickets/{ticket.id}')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Test Ticket', response.data)


if __name__ == '__main__':
    unittest.main()
