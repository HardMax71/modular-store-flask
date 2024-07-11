from flask import Blueprint, redirect, url_for, flash, render_template, Flask
from flask.typing import ResponseValue
from flask_babel import gettext as _
from flask_login import current_user

from modules.db.database import db
from modules.decorators import login_required_with_message
from modules.email import send_email
from ..db.models import Purchase

purchase_history_bp = Blueprint('purchase_history', __name__)


@purchase_history_bp.route("/")
@login_required_with_message(message=_("You must be logged in to view your purchase history."))
def purchase_history() -> ResponseValue:
    """Render the purchase history page for the current user."""
    purchases = db.session.query(Purchase).filter_by(user_id=current_user.id).order_by(Purchase.date.desc()).all()
    return render_template("history.html", purchases=purchases)


@purchase_history_bp.route("/details/<int:purchase_id>")
@login_required_with_message(message=_("You must be logged in to view purchase details."))
def purchase_details(purchase_id: int) -> tuple[str, int] | ResponseValue:
    """Render the purchase details page for a specific purchase."""
    purchase = db.session.get(Purchase, purchase_id)
    if not purchase:
        return _("Purchase not found"), 404
    if purchase.user_id != current_user.id:
        flash(_("You don't have permission to view this purchase."), "danger")
        return redirect(url_for('purchase_history.purchase_history'))
    return render_template("purchase_details.html", purchase=purchase)


@purchase_history_bp.route("/cancel-order/<int:purchase_id>", methods=['POST'])
@login_required_with_message(message=_("You must be logged in to cancel an order."))
def cancel_order(purchase_id: int) -> tuple[str, int] | ResponseValue:
    purchase = db.session.get(Purchase, purchase_id)
    if not purchase:
        return _("Purchase not found"), 404
    if purchase.user_id != current_user.id:
        flash(_("You don't have permission to cancel this order."), "danger")
        return redirect(url_for('purchase_history.purchase_history'))
    if purchase.status != 'Pending':
        flash(_("This order cannot be cancelled."), "danger")
        return redirect(url_for('purchase_history.purchase_details', purchase_id=purchase_id))

    Purchase.update_stock(purchase, reverse=True)  # Add a 'reverse' parameter to increase stock

    purchase.status = 'Cancelled'
    db.session.commit()
    send_email(current_user.email, 'Order Cancelled', 'Your order has been successfully cancelled.')
    flash(_("Order cancelled successfully."), "success")
    return redirect(url_for('purchase_history.purchase_history'))


def init_purchase_history(app: Flask) -> None:
    """Initialize the purchase history blueprint."""
    app.register_blueprint(purchase_history_bp, url_prefix='/purchase-history')
