import os
from dataclasses import dataclass
from datetime import timedelta


@dataclass
class AppConfig:
    SECRET_KEY: str = 'your_secret_key'
    PROJECT_ROOT: str = os.path.abspath(os.path.dirname(__file__))

    DEFAULT_LIMIT_RATE: str = '100 per minute'
    LOW_STOCK_THRESHOLD: int = 5

    DB_PATH: str = os.path.join(PROJECT_ROOT, 'instance')  # SQLite database file path
    DB_NAME: str = 'data.db'  # SQLite database file name
    BACKUP_DIR: str = os.path.join(PROJECT_ROOT, 'modules', 'db', 'backups')  # Backup directory
    SQLALCHEMY_DATABASE_URI: str = 'sqlite:///' + DB_PATH + '/' + DB_NAME
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    LIMITER_STORAGE_URI: str = 'memory://'

    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(minutes=15)
    SHOP_NAME: str = 'Modular Store'
    IMAGES_FOLDER: str = os.path.join('static', 'img')

    PROFILE_PICS_FOLDER: str = os.path.join(IMAGES_FOLDER, 'profile_pictures')
    DEFAULT_PROFILE_PIC: str = 'default_profile.png'

    REVIEW_PICS_FOLDER: str = os.path.join(IMAGES_FOLDER, 'review_pictures')
    DEFAULT_REVIEW_PIC: str = 'default_review.png'

    PRODUCTS_PICS_FOLDER: str = os.path.join(IMAGES_FOLDER, 'products_pictures')
    DEFAULT_PRODUCT_PIC: str = 'default_product.png'

    UPLOAD_FOLDER: str = os.path.join(IMAGES_FOLDER, 'uploads')  # Folder for uploaded images for admin emails
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16 MB max file size

    IMG_FORMATS = ['.png', '.jpg', '.jpeg', '.bmp']
    MAIL_DEFAULT_SENDER: str = 'default'
    WEBSITE_URL: str = 'https://monkfish-app-mbn3z.ondigitalocean.app/'
    PER_PAGE: int = 9  # Number of items per page shown in the shop

    TERMS_LAST_UPDATED: str = 'July 7, 2024'
    CONTACT_EMAIL: str = 'contact@example.com'
    CONTACT_PHONE: str = '123-456-7890'
    JURISDICTION: str = 'New York, NY'

    RETURN_POLICY_LAST_UPDATED: str = 'July 7, 2024'
    RETURN_WINDOW: int = 30
    RETURNS_EMAIL: str = 'return@example.com'
    REFUND_PROCESSING_DAYS: int = 7
    RETURNS_PHONE: str = '123-456-7890'

    MAIL_SERVER = 'your_mail_server'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'your_email@example.com'
    MAIL_PASSWORD = 'your_email_password'

    STRIPE_PUBLIC_KEY: str = 'your_stripe_public_key'
    STRIPE_SECRET_KEY: str = 'your_stripe_secret_key'

    LOCALE_PATH = os.getenv('LOCALE_PATH', './translations/')
    GETTEXT_DOMAIN = os.getenv('GETTEXT_DOMAIN', 'messages')
    LANGUAGES = ['en', 'ru']
    LANGUAGE_NAMES = {
        'en': 'English',
        'ru': 'Русский'
    }
    DEFAULT_LANG = 'en'

    # Flask-Dance settings
    FACEBOOK_OAUTH_CLIENT_ID: str = 'your_facebook_app_id'
    FACEBOOK_OAUTH_CLIENT_SECRET: str = 'your_facebook_app_secret'
    GOOGLE_OAUTH_CLIENT_ID: str = 'your_google_client_id'
    GOOGLE_OAUTH_CLIENT_SECRET: str = 'your_google_client_secret'

    # Social media links
    FACEBOOK_URL = 'https://www.facebook.com/your_facebook_page'
    TWITTER_URL = 'https://twitter.com/your_twitter_page'
    INSTAGRAM_URL = 'https://www.instagram.com/your_instagram_page'
