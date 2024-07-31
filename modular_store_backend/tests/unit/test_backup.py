# /modular_store_backend/tests/unit/test_backup.py
import unittest
from unittest.mock import patch

from flask import Flask

from modular_store_backend.modules.db.backup import backup_database


class TestBackup(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['BACKUP_DIR'] = '/tmp/backups'
        self.app.config['DB_PATH'] = '/tmp/test.db'

    @patch('modular_store_backend.modules.db.backup.os.path.exists')
    @patch('modular_store_backend.modules.db.backup.os.makedirs')
    @patch('modular_store_backend.modules.db.backup.shutil.copyfile')
    def test_backup_database_success(self, mock_copyfile, mock_makedirs, mock_exists):
        mock_exists.return_value = False

        backup_database(self.app)

        mock_exists.assert_called_once_with('/tmp/backups')
        mock_makedirs.assert_called_once_with('/tmp/backups')
        self.assertTrue(mock_copyfile.call_args[0][0].endswith('test.db'))
        self.assertTrue(mock_copyfile.call_args[0][1].startswith('/tmp/backups'))

    @patch('modular_store_backend.modules.db.backup.os.path.exists')
    @patch('modular_store_backend.modules.db.backup.shutil.copyfile')
    def test_backup_database_existing_dir(self, mock_copyfile, mock_exists):
        mock_exists.return_value = True

        backup_database(self.app)

        mock_exists.assert_called_once_with('/tmp/backups')
        mock_copyfile.assert_called_once()

    @patch('modular_store_backend.modules.db.backup.os.path.exists')
    @patch('modular_store_backend.modules.db.backup.shutil.copyfile')
    def test_backup_database_error(self, mock_copyfile, mock_exists):
        mock_exists.return_value = True
        mock_copyfile.side_effect = Exception("Test exception")

        with self.assertLogs() as captured:
            backup_database(self.app)

        self.assertIn("Error creating database backup: Test exception", captured.output[0])
