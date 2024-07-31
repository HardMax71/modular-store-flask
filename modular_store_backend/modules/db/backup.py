# /modular_store_backend/modules/db/backup.py
import logging
import os
import shutil
from datetime import datetime

from flask import Flask


def backup_database(app: Flask) -> None:
    # if not exists - create folder
    if not os.path.exists(app.config['BACKUP_DIR']):
        os.makedirs(app.config['BACKUP_DIR'])

    # Create a timestamp for the backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create the backup filename
    backup_file = f"database_backup_{timestamp}.db"

    # Create the backup file path
    backup_path = os.path.join(app.config['BACKUP_DIR'], backup_file)

    try:
        # Copy the database file to the backup directory with the specified backup filename
        shutil.copyfile(app.config['DB_PATH'], backup_path)
        logging.info(f"Database backup created: {backup_path}")
    except Exception as e:
        logging.error(f"Error creating database backup: {str(e)}")

# Run the backup function
# backup_database()
# print('backup turned off in backup.py')
