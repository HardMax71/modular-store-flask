import unittest

from flask import request
from flask_login import login_user, logout_user
from werkzeug.datastructures import LanguageAccept

from modular_store_backend.modules.extensions.utils import get_locale, load_user
from modular_store_backend.tests.base_test import BaseTest
from modular_store_backend.tests.util import create_user


class TestExtensionsUnit(BaseTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=False, define_load_user=True)

    def test_get_locale_authenticated(self):
        with self.app.test_request_context():
            user = create_user(self, language='fr')

            login_user(user)
            self.assertEqual(get_locale(), 'fr')
            logout_user()

    def test_get_locale_unauthenticated(self):
        with self.app.test_request_context():
            # Simulate an Accept-Language header
            request.accept_languages = LanguageAccept([('en', 1), ('ru', 0.8)])
            self.assertEqual(get_locale(), 'en')  # Assuming 'en' is in LANGUAGES

            # Test with a non-supported language
            request.accept_languages = LanguageAccept([('fr', 1), ('de', 0.8)])
            self.assertEqual(get_locale(), self.app.config['DEFAULT_LANG'])  # Should fall back to default

    def test_load_user(self):
        user = create_user(self)

        loaded_user = load_user(user.id)
        self.assertEqual(loaded_user, user)

    def test_load_user_not_found(self):
        non_existent_id = 9999  # Assuming this ID doesn't exist
        loaded_user = load_user(non_existent_id)
        self.assertIsNone(loaded_user)


if __name__ == '__main__':
    unittest.main()
