# /modular_store_backend/tests/unit/test_decorators.py
import random
import unittest

from flask import Flask
from flask import render_template_string
from flask_babel import Babel  # type: ignore
from flask_login import LoginManager, UserMixin, login_user, logout_user  # type: ignore
from werkzeug.datastructures import Headers

from modular_store_backend.app import load_config
from modular_store_backend.modules.decorators import login_required_with_message, admin_required


# Helper function to render a template with flashed messages
def render_with_messages(content):
    template = '''
    <!DOCTYPE html>
    <html>
    <body>
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
        <ul class="flashes">
            {% for category, message in messages %}
            <li class="{{ category }}">{{ message }}</li>
            {% endfor %}
        </ul>
        {% endif %}
        {% endwith %}
        <div>{{ content }}</div>
    </body>
    </html>
    '''
    return render_template_string(template, content=content)


class User(UserMixin):
    def __init__(self, id):
        self.id = id
        self.is_admin = False


class TestDecorators(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        config = load_config('./modular_store_backend/config.yaml')
        cls.app.config.update(config)
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.app.config['SECRET_KEY'] = 'test_secret_key'

        login_manager = LoginManager()
        login_manager.init_app(cls.app)

        babel = Babel(cls.app)  # required by many tests below
        print(babel)

        @login_manager.user_loader
        def load_user(user_id):
            return User(int(user_id))

        @cls.app.route('/')
        def index():
            return render_with_messages('Index Page')

        @cls.app.route('/protected')
        @login_required_with_message(default_route='index')
        def protected_route():
            return render_with_messages('Protected Content')

        @cls.app.route('/custom-protected')
        @login_required_with_message(message="Custom login message", category="info", default_route='index')
        def custom_protected_route():
            return render_with_messages('Custom Protected Content')

        @cls.app.route('/redirect-protected')
        @login_required_with_message(redirect_back=True, default_route='index')
        def redirect_protected_route():
            return render_with_messages('Redirect Protected Content')

        @cls.app.route('/admin-only')
        @admin_required(default_route='index')
        def admin_only_route():
            return render_with_messages('Admin Only Content')

    def setUp(self):
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.request_context = self.app.test_request_context()
        self.request_context.push()

    def tearDown(self):
        self.request_context.pop()
        self.app_context.pop()

    def test_login_required_with_message(self):
        # Test unauthenticated access
        response = self.client.get('/protected', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Index Page', response.data.decode())
        self.assertIn('You must be logged in to view this page.', response.data.decode())
        self.assertIn('class="danger"', response.data.decode())

        # Test authenticated access
        user = User(random.randint(1, 1000))
        login_user(user)

        response = self.client.get('/protected')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Protected Content', response.data.decode())
        self.assertNotIn('You must be logged in to view this page.', response.data.decode())

    def test_login_required_with_custom_message(self):
        logout_user()
        response = self.client.get('/custom-protected', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Index Page', response.data.decode())
        self.assertIn('Custom login message', response.data.decode())
        self.assertIn('class="info"', response.data.decode())

    def test_login_required_redirect_back(self):
        headers = Headers()
        headers.add('Referer', '/previous-page')
        response = self.client.get('/redirect-protected', headers=headers)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/previous-page')

    def test_admin_required(self):
        # Test unauthenticated access
        response = self.client.get('/admin-only', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Index Page', response.data.decode())
        self.assertIn("You don&#39;t have permission to access this page.", response.data.decode())
        self.assertIn('class="warning"', response.data.decode())

        # Test non-admin authenticated access
        user = User(random.randint(1, 1000))
        login_user(user)

        response = self.client.get('/admin-only', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Index Page', response.data.decode())
        self.assertIn("You don&#39;t have permission to access this page.", response.data.decode())
        self.assertIn('class="warning"', response.data.decode())

        # Test admin authenticated access
        logout_user()
        admin_user = User(random.randint(1001, 2000))
        admin_user.is_admin = True
        login_user(admin_user)

        response = self.client.get('/admin-only')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Admin Only Content', response.data.decode())
        self.assertNotIn("You don&#39;t have permission to access this page.", response.data.decode())


if __name__ == '__main__':
    unittest.main()
