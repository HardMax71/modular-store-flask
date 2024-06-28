from functools import wraps

from flask import flash, redirect, request, url_for
from flask_babel import gettext as _
from flask_login import current_user


def login_required_with_message(message=_("You must be logged in to view this page."),
                                category="danger",
                                redirect_back=False,
                                default_route="main.index"):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash(_(message), category)
                if redirect_back:
                    # Redirect to the referring page
                    referrer = request.headers.get("Referer")
                    if referrer:
                        return redirect(referrer)
                    return redirect(url_for(default_route))
                return redirect(url_for(default_route))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(default_route="main.index"):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_admin:
                flash(_("You don't have permission to access this page."), "warning")
                return redirect(url_for(default_route))
            return f(*args, **kwargs)

        return decorated_function
    return decorator
