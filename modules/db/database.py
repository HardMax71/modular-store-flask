import os
import shutil

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from config import AppConfig

Base = declarative_base()

engine = create_engine(AppConfig.SQLALCHEMY_DATABASE_URI, connect_args={"check_same_thread": False})
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base.query = db_session.query_property()


def ensure_data_db_exists(backup_dir=AppConfig.BACKUP_DIR, data_db_path=AppConfig.DB_PATH,
                          db_file_name=AppConfig.DB_NAME):
    if not os.path.exists(data_db_path):
        os.makedirs(data_db_path)

    data_db_file = os.path.join(data_db_path, db_file_name)

    if os.path.isfile(data_db_file):
        print("Database file already exists")
        return

    backup_files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.endswith(".db")]

    if backup_files:
        latest_backup = max(backup_files, key=os.path.getmtime)
        shutil.copy(latest_backup, data_db_file)
    else:
        open(data_db_file, "a").close()


def init_db():
    ensure_data_db_exists()
    Base.metadata.create_all(bind=engine)
