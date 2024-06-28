import time

from flask import current_app
from flask import request
from flask_login import current_user

from modules.db.database import db
from modules.db.models import RequestLog


class DatabaseLogger(object):
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self):
        request.start_time = time.time()

    def after_request(self, response):
        execution_time = time.time() - request.start_time
        user_id = current_user.id if current_user.is_authenticated else None

        # Handle the case when request.endpoint is None
        endpoint = request.endpoint if request.endpoint else 'unknown'

        log_data = {
            'user_id': user_id,
            'ip_address': request.remote_addr,
            'endpoint': endpoint,
            'method': request.method,
            'status_code': response.status_code,
            'execution_time': execution_time
        }
        current_app.logger.info(f"Request: {log_data}")
        db.session.add(RequestLog(**log_data))
        db.session.commit()
        return response
