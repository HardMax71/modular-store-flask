import os
import shutil
from datetime import datetime

from config import AppConfig


def backup_database(backup_dir=AppConfig.BACKUP_DIR):
    # if not exists - create folder
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # Create a timestamp for the backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create the backup filename
    backup_file = f"database_backup_{timestamp}.db"

    # Create the backup file path
    backup_path = os.path.join(backup_dir, backup_file)

    try:
        # Copy the database file to the backup directory with the specified backup filename
        shutil.copyfile(AppConfig.DB_PATH + '/' + AppConfig.DB_NAME, backup_path)
        print(f"Database backup created: {backup_path}")
    except Exception as e:
        print(f"Error creating database backup: {str(e)}")


# Run the backup function
# backup_database()
print('backup turned off in backup.py')
