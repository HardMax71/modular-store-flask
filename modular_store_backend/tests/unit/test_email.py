from smtplib import SMTPException
from unittest.mock import patch, MagicMock

from flask_mail import BadHeaderError

from modular_store_backend.modules.email import send_email, send_wishlist_email, send_order_confirmation_email
from modular_store_backend.tests.base_test import BaseTest


class TestEmail(BaseTest):
    @patch('modular_store_backend.modules.email.current_app')
    def test_send_email(self, mock_current_app):
        # Fix: Create MagicMock instead of AsyncMock
        mock_mail = MagicMock()
        mock_current_app.extensions = {'mail': mock_mail}

        # Test basic email without attachments
        send_email('test@example.com', 'Test Subject', 'Test Body')
        mock_mail.send.assert_called_once()

        # Reset mock for next test
        mock_mail.reset_mock()

        # Test with attachments
        with patch('modular_store_backend.modules.email.os') as mock_os:
            # Mock file opening
            mock_file = MagicMock()
            mock_open = MagicMock(return_value=mock_file)
            mock_current_app.open_resource = MagicMock(return_value=mock_open)
            mock_current_app.open_resource.return_value.__enter__.return_value = mock_file

            # We need to mock the with context
            mock_open = MagicMock()
            mock_open.__enter__.return_value = mock_file
            mock_current_app.open_resource.return_value = mock_open

            send_email('test@example.com', 'Test Subject', 'Test Body', ['file.txt'])
            self.assertEqual(mock_mail.send.call_count, 1)

    @patch('modular_store_backend.modules.email.current_app')
    @patch('modular_store_backend.modules.email.flash')
    @patch('modular_store_backend.modules.email._')  # Mock gettext
    @patch('flask_login.current_user')  # Use the correct import path!
    def test_send_wishlist_email(self, mock_current_user, mock_gettext, mock_flash, mock_current_app):
        # Setup authentication status
        mock_current_user.is_authenticated = True
        mock_current_user.language = 'en'

        # Make gettext return the input string
        mock_gettext.side_effect = lambda x: x

        mock_mail = MagicMock()
        mock_current_app.extensions = {'mail': mock_mail}

        # Test successful sending
        msg = MagicMock()
        send_wishlist_email(msg)
        mock_mail.send.assert_called_once_with(msg)
        mock_flash.assert_called_once()

    @patch('modular_store_backend.modules.email.current_app')
    @patch('modular_store_backend.modules.email.flash')
    @patch('modular_store_backend.modules.email.Message')
    @patch('modular_store_backend.modules.email.current_user')  # Fix: Mock current_user
    @patch('modular_store_backend.modules.email._')  # Fix: Mock gettext
    def test_send_order_confirmation_email(self, mock_gettext, mock_current_user, mock_message, mock_flash,
                                           mock_current_app):
        # Setup authentication status
        mock_current_user.is_authenticated = True
        mock_current_user.language = 'en'

        # Setup gettext to return the original string
        mock_gettext.side_effect = lambda x: x

        mock_mail = MagicMock()
        mock_current_app.extensions = {'mail': mock_mail}
        mock_current_app.config = {'MAIL_DEFAULT_SENDER': 'test@example.com'}

        # Test successful sending
        send_order_confirmation_email('customer@example.com', 'Test User')
        mock_message.assert_called_once()
        mock_mail.send.assert_called_once()
        mock_flash.assert_called_once()

        # Test with exceptions
        for exception_class in [BadHeaderError, SMTPException, Exception]:
            mock_message.reset_mock()
            mock_mail.reset_mock()
            mock_flash.reset_mock()
            mock_mail.send.side_effect = exception_class("Test error")

            send_order_confirmation_email('customer@example.com', 'Test User')
            mock_message.assert_called_once()
            mock_flash.assert_called_once()
