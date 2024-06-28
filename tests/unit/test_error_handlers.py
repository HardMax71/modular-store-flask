import unittest
from unittest.mock import patch

from werkzeug.exceptions import NotFound, InternalServerError

from app import create_app
from config import AppConfig
from modules.error_handlers.handlers import handle_error, error_handlers_bp


class TestErrorHandlersUnit(unittest.TestCase):
    def setUp(self):
        AppConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        self.app = create_app(AppConfig)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_create_error_handlers(self):
        self.assertIn(400, self.app.error_handler_spec[None])
        self.assertIn(404, self.app.error_handler_spec[None])
        self.assertIn(500, self.app.error_handler_spec[None])

    @patch('modules.error_handlers.handlers.render_template')
    def test_handle_error_404(self, mock_render):
        mock_render.return_value = 'Error page'
        with self.app.test_request_context('/nonexistent'):
            response, status_code = handle_error(NotFound())
            self.assertEqual(status_code, 404)
            mock_render.assert_called_once()
            self.assertIn('error', mock_render.call_args[1])

    @patch('modules.error_handlers.handlers.render_template')
    def test_handle_error_500(self, mock_render):
        mock_render.return_value = 'Error page'
        with self.app.test_request_context('/'):
            response, status_code = handle_error(InternalServerError())
            self.assertEqual(status_code, 500)
            mock_render.assert_called_once()
            self.assertIn('error', mock_render.call_args[1])

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

    def test_init_error_handlers(self):
        self.assertIn(400, self.app.error_handler_spec[None])
        self.assertIn(404, self.app.error_handler_spec[None])
        self.assertIn(500, self.app.error_handler_spec[None])
        self.assertIn(error_handlers_bp.name, self.app.blueprints)
        self.assertIsNotNone(error_handlers_bp.logger)


if __name__ == '__main__':
    unittest.main()
