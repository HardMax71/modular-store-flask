from functools import wraps
from typing import Callable, Any

from flask import flash, redirect, request, url_for
from flask_babel import gettext as _
from flask_login import current_user

# Type alias for a route handler
RouteHandler = Callable[..., Any]


def login_required_with_message(message: str = _("You must be logged in to view this page."),
                                category: str = "danger",
                                redirect_back: bool = False,
                                default_route: str = "main.index") -> Callable[[RouteHandler], RouteHandler]:
    """
    Decorator to require login with a flash message and optional redirect.

    :param message: Flash message to display
    :param category: Flash message category
    :param redirect_back: Redirect back to the referring page if True
    :param default_route: Default route to redirect to if no referrer
    :return: Decorated route handler
    """

    def decorator(f: RouteHandler) -> RouteHandler:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any):  # type: ignore
            if not current_user.is_authenticated:
                flash(_(message), category)
                if redirect_back:
                    if referrer := request.headers.get("Referer", None):
                        return redirect(referrer)
                return redirect(url_for(default_route))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(default_route: str = "main.index") -> Callable[[RouteHandler], RouteHandler]:
    """
    Decorator to require admin access.

    :param default_route: Default route to redirect to if not authorized
    :return: Decorated route handler
    """

    def decorator(f: RouteHandler) -> RouteHandler:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            if not current_user.is_authenticated or not current_user.is_admin:
                flash(_("You don't have permission to access this page."), "warning")
                return redirect(url_for(default_route))
            return f(*args, **kwargs)

        return decorated_function

    return decorator
