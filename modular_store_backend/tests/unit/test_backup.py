import unittest
from unittest.mock import patch, MagicMock
import os

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
    @patch('modular_store_backend.modules.db.backup.logging.info')
    def test_backup_database_success(self, mock_logging_info, mock_copyfile, mock_makedirs, mock_exists):
        mock_exists.return_value = False

        # Patch datetime to return a fixed timestamp
        with patch('modular_store_backend.modules.db.backup.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20250225_144524"
            backup_database(self.app)

            mock_exists.assert_called_once_with('/tmp/backups')
            mock_makedirs.assert_called_once_with('/tmp/backups')
            mock_copyfile.assert_called_once_with('/tmp/test.db',
                os.path.join('/tmp/backups', 'database_backup_20250225_144524.db'))

            # Verify logging.info is called with the correct message
            expected_path = os.path.normpath('/tmp/backups/database_backup_20250225_144524.db')
            expected_message = f"Database backup created: {expected_path}"
            mock_logging_info.assert_called_once_with(expected_message)

    @patch('modular_store_backend.modules.db.backup.os.path.exists')
    @patch('modular_store_backend.modules.db.backup.shutil.copyfile')
    @patch('modular_store_backend.modules.db.backup.logging.error')
    def test_backup_database_error(self, mock_logging_error, mock_copyfile, mock_exists):
        mock_exists.return_value = True
        mock_copyfile.side_effect = Exception("Test exception")

        backup_database(self.app)

        mock_logging_error.assert_called_once()
        self.assertIn("Error creating database backup", mock_logging_error.call_args[0][0])
