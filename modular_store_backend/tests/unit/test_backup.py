import unittest
from unittest.mock import patch, MagicMock

from modular_store_backend.modules.db.backup import backup_database


class TestBackup(unittest.TestCase):
    def setUp(self):
        self.app = MagicMock()
        self.app.config = {
            'BACKUP_DIR': '/tmp/backups',
            'DB_PATH': '/tmp/test.db'
        }

    @patch('modular_store_backend.modules.db.backup.os.path.exists')
    @patch('modular_store_backend.modules.db.backup.os.makedirs')
    @patch('modular_store_backend.modules.db.backup.shutil.copyfile')
    @patch('modular_store_backend.modules.db.backup.print')  # Patch print instead of logging
    def test_backup_database_success(self, mock_print, mock_copyfile, mock_makedirs, mock_exists):
        mock_exists.return_value = False

        # Use datetime to create a fixed timestamp for testing
        with patch('modular_store_backend.modules.db.backup.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20250225_144524"

            backup_database(self.app)

            mock_exists.assert_called_once_with('/tmp/backups')
            mock_makedirs.assert_called_once_with('/tmp/backups')
            mock_copyfile.assert_called_once()
            self.assertEqual(mock_copyfile.call_args[0][0], '/tmp/test.db')

            # Use os.path.normpath to handle path separators correctly
            import os
            expected_path = os.path.normpath('/tmp/backups/database_backup_20250225_144524.db')
            actual_path = os.path.normpath(mock_copyfile.call_args[0][1])
            self.assertEqual(actual_path, expected_path)

            mock_print.assert_called_once()

    @patch('modular_store_backend.modules.db.backup.os.path.exists')
    @patch('modular_store_backend.modules.db.backup.shutil.copyfile')
    @patch('modular_store_backend.modules.db.backup.print')  # Patch print instead of logging
    def test_backup_database_error(self, mock_print, mock_copyfile, mock_exists):
        mock_exists.return_value = True
        mock_copyfile.side_effect = Exception("Test exception")

        backup_database(self.app)

        mock_print.assert_called_once()
        self.assertIn("Error creating database backup", mock_print.call_args[0][0])