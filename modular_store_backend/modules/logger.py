# /modular_store_backend/modules/logger.py
import time
from typing import Optional

from flask import current_app, Flask, request, Response
from flask_login import current_user

from modular_store_backend.modules.db.database import db
from modular_store_backend.modules.db.models import RequestLog


class DatabaseLogger:
    """
    Logger class to log request details into the database.
    """

    def __init__(self, app: Optional[Flask] = None) -> None:
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self) -> None:
        request.start_time = time.time()  # type: ignore

    def after_request(self, response: Response) -> Response:
        execution_time = time.time() - request.start_time  # type: ignore
        user_id = current_user.id if current_user.is_authenticated else None
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
