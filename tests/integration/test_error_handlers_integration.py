import unittest
from unittest.mock import patch

from werkzeug.exceptions import NotFound, InternalServerError

from modules.error_handlers.handlers import handle_error, error_handlers_bp
from tests.base_test import BaseTest


class TestErrorHandlersIntegration(BaseTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass(init_login_manager=False, define_load_user=True)

        # Add a route that deliberately raises an exception
        @cls.app.route('/trigger-error')
        def trigger_error():
            raise Exception("Deliberate 500 error")

    def test_init_error_handlers(self):
        self.assertIn(400, self.app.error_handler_spec[None])
        self.assertIn(404, self.app.error_handler_spec[None])
        self.assertIn(500, self.app.error_handler_spec[None])
        self.assertIn(error_handlers_bp.name, self.app.blueprints)
        self.assertIsNotNone(error_handlers_bp.logger)

    def test_404_error(self):
        response = self.client.get('/nonexistent-page')
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'The server cannot find the requested page', response.data)

    def test_500_error(self):
        with self.app.test_client() as client:
            # Disable exception handling for this test
            client.application.config['TESTING'] = False
            response = client.get('/trigger-error')
            self.assertEqual(response.status_code, 500)
            self.assertIn(b'The server has encountered a situation it doesn\'t know how to handle', response.data)

    def test_error_without_user_session(self):
        response = self.client.get('/nonexistent-page')
        self.assertIn(b'Error type: 404', response.data)

    def test_error_with_user_session(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
        response = self.client.get('/nonexistent-page')
        self.assertIn(b'Error type: 404', response.data)

    def test_error_includes_request_url(self):
        response = self.client.get('/nonexistent-page')
        self.assertIn(b'/nonexistent-page', response.data)

    @patch('modules.error_handlers.handlers.render_template')
    def test_handle_error_with_traceback(self, mock_render):
        mock_render.return_value = 'Error page'
        with self.app.test_request_context('/'):
            exception = Exception("Test exception")
            error = InternalServerError(original_exception=exception)
            response, status_code = handle_error(error)
            self.assertEqual(status_code, 500)
            self.assertIn('traceback', mock_render.call_args[1])

    @patch('modules.error_handlers.handlers.error_handlers_bp.logger.log')
    def test_error_logging(self, mock_log):
        with self.app.test_request_context('/'):
            handle_error(NotFound())
            mock_log.assert_called_once()
            log_message = mock_log.call_args[1]['msg']
            self.assertIn('Error type: 404', log_message)


if __name__ == '__main__':
    unittest.main()
