# /modular_store_backend/modules/oauth_login.py
from authlib.integrations.flask_client import OAuth
from flask import Flask

oauth = OAuth()


def init_oauth(app: Flask) -> None:
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
        client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    oauth.register(
        name='facebook',
        client_id=app.config['FACEBOOK_OAUTH_CLIENT_ID'],
        client_secret=app.config['FACEBOOK_OAUTH_CLIENT_SECRET'],
        access_token_url='https://graph.facebook.com/oauth/access_token',
        access_token_params=None,
        authorize_url='https://www.facebook.com/dialog/oauth',
        authorize_params=None,
        api_base_url='https://graph.facebook.com/',
        client_kwargs={'scope': 'email'},
    )
