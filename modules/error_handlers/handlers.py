from flask import Blueprint, request, session, render_template

error_handlers_bp = Blueprint('error_handlers', __name__)

error_explanations = {
    400: "The server could not understand the request due to invalid syntax.",
    401: "The request has not been applied because it lacks valid authentication credentials for the target resource.",
    403: "Access to the requested resource is forbidden.",
    404: "The server cannot find the requested page.",
    429: "Too many requests. Please try again later.",
    491: "The server cannot handle the request due to a temporary overloading or maintenance of the server.",
    500: "The server has encountered a situation it doesn't know how to handle."
}


def handle_error(e):
    error_code = e.code if hasattr(e, 'code') else 500
    ip = request.remote_addr

    error_message = f"Error type: {error_code}\n{error_explanations.get(error_code, 'Error!')}\nIP: {ip}"

    error_handlers_bp.logger.log(level=1, msg=error_message.replace('<br>', '\n'))

    request_url = request.url
    dont_show = 'user_id' not in session

    traceback = None
    if error_code == 500:
        original_exception = getattr(e, 'original_exception', e.args)
        if original_exception:
            traceback = str(original_exception)

    return render_template('website_parts/error_page.html', error=error_message,
                           request_url=request_url, dont_show=dont_show,
                           traceback=traceback), error_code


def init_error_handlers(app):
    for error_code in [400, 401, 403, 404, 429, 500]:
        app.register_error_handler(error_code, handle_error)

    app.register_blueprint(error_handlers_bp)
    error_handlers_bp.logger = app.logger
