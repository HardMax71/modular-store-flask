from typing import Dict, Union, Optional

from flask import Blueprint, request, session, render_template
from flask import Flask
from werkzeug.exceptions import HTTPException

error_handlers_bp = Blueprint('error_handlers', __name__)

# Dictionary mapping error codes to their explanations
error_explanations: Dict[int, str] = {
    400: "The server could not understand the request due to invalid syntax.",
    401: "The request has not been applied because it lacks valid authentication credentials for the target resource.",
    403: "Access to the requested resource is forbidden.",
    404: "The server cannot find the requested page.",
    429: "Too many requests. Please try again later.",
    500: "The server has encountered a situation it doesn't know how to handle."
}


def handle_error(e: Union[HTTPException, Exception]) -> tuple[str, int]:
    """
    Handle various HTTP errors and return appropriate error pages.

    Args:
        e (Union[HTTPException, Exception]): The exception that occurred.

    Returns:
        tuple[str, int]: A tuple containing the rendered error template and the HTTP status code.
    """
    error_code: int = e.code if hasattr(e, 'code') else 500
    ip: Optional[str] = request.remote_addr

    error_message: str = (f"Error type: {error_code}\n"
                          f"{error_explanations.get(error_code, 'Error!')}\n"
                          f"IP: {ip or 'Unknown IP'}")

    request_url: str = request.url
    dont_show: bool = 'user_id' not in session

    traceback: Optional[str] = None
    if error_code == 500:
        original_exception = getattr(e, 'original_exception', e.args)
        if original_exception:
            traceback = str(original_exception)

    return render_template('website_parts/error_page.html',
                           error=error_message,
                           request_url=request_url,
                           dont_show=dont_show,
                           traceback=traceback), error_code


def init_error_handlers(app: Flask) -> None:
    """
    Initialize error handlers for the Flask application.

    Args:
        app (Flask): The Flask application instance.
    """
    for error_code in error_explanations.keys():
        app.register_error_handler(error_code, handle_error)

    app.register_blueprint(error_handlers_bp)
