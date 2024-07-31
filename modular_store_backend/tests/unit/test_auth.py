# /modular_store_backend/tests/unit/test_auth.py
from unittest.mock import patch, MagicMock

from flask import session
from flask_login import current_user, login_user, logout_user
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from werkzeug.security import check_password_hash

from modular_store_backend.modules.db.models import User
from modular_store_backend.tests.base_test import BaseTest
from modular_store_backend.tests.util import create_user


class TestAuth(BaseTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=True, csrf_enabled=False, define_load_user=True)

    def setUp(self):
        super().setUp()
        self.user = create_user(self, username='testuser', email='test@example.com', password='password123')

    def test_register(self):
        response = self.client.post('/register', data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpassword123',
            'confirm_password': 'newpassword123'
        }, follow_redirects=True)
        assert b"Registration successful. Please log in." in response.data
        new_user = self.session.query(User).filter_by(username='newuser').first()
        assert new_user is not None
        assert new_user.email == 'newuser@example.com'

    def test_register_existing_username(self):
        response = self.client.post('/register', data={
            'username': 'testuser',
            'email': 'another@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        assert b"Username already exists. Please choose a different one." in response.data

    def test_register_password_mismatch(self):
        response = self.client.post('/register', data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'password123',
            'confirm_password': 'password456'
        }, follow_redirects=True)
        assert b"Field must be equal to password." in response.data

    def test_login(self):
        with self.app.test_request_context():
            response = self.client.post('/login', data={
                'username': 'testuser',
                'password': 'password123'
            }, follow_redirects=True)
            assert b"Login successful." in response.data
            assert current_user.is_authenticated
            assert current_user.username == 'testuser'

    def test_login_invalid_credentials(self):
        with self.app.test_request_context():
            logout_user()

            response = self.client.post('/login', data={
                'username': 'testuser',
                'password': 'wrongpassword'
            }, follow_redirects=True)
            assert b"Invalid username or password." in response.data
            assert not current_user.is_authenticated

    def test_logout(self):
        with self.app.test_request_context():
            login_user(self.user)
            response = self.client.get('/logout', follow_redirects=True)
            assert b"You have been logged out." in response.data
            assert not current_user.is_authenticated

    # I haven't added mail server creds tio test website, so now it returns:
    #  "Sending email is disabled for now" in response.data
    # def test_reset_password_request(self):
    #     with patch('flask_mail.Mail.send') as mock_send:
    #         response = self.client.post('/reset_password', data={
    #             'email': 'test@example.com'
    #         }, follow_redirects=True)
    #         assert b"Password reset email sent. Please check your inbox." in response.data
    #         mock_send.assert_called_once()

    def test_reset_password_token(self):
        s = URLSafeTimedSerializer(self.app.config['SECRET_KEY'])
        token = s.dumps({'user_id': self.user.id})
        response = self.client.post(f'/reset_password/{token}', data={
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        }, follow_redirects=True)
        assert b"Your password has been reset. You can now log in with the new password." in response.data
        self.user = self.session.query(User).get(self.user.id)  # Refresh user from database
        assert check_password_hash(self.user.password, 'newpassword123')

    def test_reset_password_token_expired(self):
        with patch('itsdangerous.URLSafeTimedSerializer.loads') as mock_loads:
            mock_loads.side_effect = SignatureExpired('Token expired')
            with self.client as c:
                response = c.get('/reset_password/faketoken', follow_redirects=True)
                assert b"Reset Your Password" in response.data
                assert 'The password reset token has expired' in session['_flashes'][0][1] or \
                       'Invalid or expired token' in session['_flashes'][0][1]

    def test_reset_password_token_invalid(self):
        with patch('itsdangerous.URLSafeTimedSerializer.loads') as mock_loads:
            mock_loads.side_effect = BadSignature('Invalid token')
            with self.client as c:
                response = c.get('/reset_password/faketoken', follow_redirects=True)
                assert b"Reset Your Password" in response.data
                assert 'Invalid token' in session['_flashes'][0][1] or \
                       'Invalid or expired token' in session['_flashes'][0][1]

    @patch('modular_store_backend.modules.oauth_login.oauth')
    def test_google_login(self, mock_oauth):
        mock_client = MagicMock()
        mock_oauth.create_client.return_value = mock_client
        mock_client.authorize_redirect.return_value = 'https://accounts.google.com/o/oauth2/v2/auth'

        response = self.client.get('/login/google')
        assert response.status_code == 302
        assert response.headers['Location'].startswith('https://accounts.google.com/o/oauth2/v2/auth')
