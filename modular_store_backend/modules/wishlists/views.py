from typing import Optional

from flask import Blueprint, redirect, request, flash, url_for, Flask
from flask.typing import ResponseValue
from flask_babel import gettext as _
from flask_login import current_user

from modular_store_backend.modules.decorators import login_required_with_message
from modular_store_backend.modules.email import send_wishlist_notifications
from modular_store_backend.modules.wishlists.utils import (
    get_product_selection_options, item_exists_in_wishlist, remove_item_from_wishlist, add_item_to_wishlist
)

wishlist_bp = Blueprint('wishlists', __name__)


@wishlist_bp.route("/wishlist", methods=["POST"])
@login_required_with_message(message=_("You must be logged in to add items to your wishlist."), redirect_back=True)
def wishlist() -> ResponseValue:
    """Add or remove an item from the user's wishlist."""
    product_id: Optional[int] = request.form.get('product_id', type=int)

    if product_id is None:
        flash(_("Invalid product. Please try again."), "danger")
        return redirect(request.referrer or url_for('main.index'))

    variant_options: dict[str, str] = get_product_selection_options(request.form.get('variant_options'))
    user_id: int = current_user.id

    if item_exists_in_wishlist(user_id, product_id):
        remove_item_from_wishlist(user_id, product_id)
        flash(_("Product removed from your wishlist."), "success")
    else:
        add_item_to_wishlist(user_id, product_id, variant_options)
        flash(_("Product added to your wishlist!"), "success")

    return redirect(url_for('profile.profile_info', id=product_id))


@wishlist_bp.route("/send-wishlist-notifications")
def send_notifications() -> ResponseValue:
    send_wishlist_notifications()
    return redirect(url_for('profile.profile_info'))


def init_wishlist(app: Flask) -> None:
    app.register_blueprint(wishlist_bp)
