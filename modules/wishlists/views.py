from typing import Optional

from flask import Blueprint, redirect, request, flash, url_for, Flask
from flask.typing import ResponseValue
from flask_babel import gettext as _
from flask_login import current_user

from modules.decorators import login_required_with_message
from modules.email import send_wishlist_notifications
from .utils import get_variant_options, wishlist_exists, remove_from_wishlist, add_wishlist_item

wishlist_bp = Blueprint('wishlists', __name__)


@wishlist_bp.route("/wishlist", methods=["POST"])
@login_required_with_message(message=_("You must be logged in to add items to your wishlist."), redirect_back=True)
def wishlist() -> ResponseValue:
    """Add or remove an item from the user's wishlist."""
    goods_id: Optional[int] = request.form.get('goods_id', type=int)

    if goods_id is None:
        flash(_("Invalid product. Please try again."), "danger")
        return redirect(request.referrer or url_for('main.index'))

    variant_options: dict[str, str] = get_variant_options(request.form.get('variant_options'))
    user_id: int = current_user.id

    if wishlist_exists(user_id, goods_id):
        remove_from_wishlist(user_id, goods_id)
        flash(_("Product removed from your wishlist."), "success")
    else:
        add_wishlist_item(user_id, goods_id, variant_options)
        flash(_("Product added to your wishlist!"), "success")

    return redirect(url_for('profile.profile_info', id=goods_id))


@wishlist_bp.route("/send-wishlist-notifications")
def send_notifications() -> ResponseValue:
    """Send notifications for wishlist items."""
    send_wishlist_notifications()
    return redirect(url_for('profile.profile_info'))


def init_wishlist(app: Flask) -> None:
    """Initialize the wishlist blueprint."""
    app.register_blueprint(wishlist_bp)
