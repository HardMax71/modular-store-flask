import json
from typing import Optional, Dict, Any, List

import stripe
from flask import Blueprint, jsonify, redirect, request, url_for, flash, render_template, Flask, current_app
from flask.typing import ResponseValue
from flask_babel import gettext as _
from flask_login import current_user

from config import AppConfig
from modules.carts.utils import (process_payment, remove_from_cart, update_cart, add_to_cart,
                                 process_successful_payment, handle_unsuccessful_payment, handle_stripe_error)
from modules.db.database import db
from modules.db.models import Product, Cart, ShippingMethod, Purchase
from modules.decorators import login_required_with_message

cart_bp = Blueprint('carts', __name__)


@cart_bp.app_template_filter('from_json')
def from_json(value) -> Dict[str, Any] | None:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


@cart_bp.route("/add-to-cart", methods=["POST"])
@login_required_with_message(redirect_back=True)
def add_to_cart_route() -> ResponseValue:
    quantity: int = request.form.get('quantity', type=int, default=1)
    product_id: Optional[int] = request.form.get('product_id', type=int)

    variant_options: Dict[str, str] = {
        key.split('variant_')[1]: value
        for key, value in request.form.items() if key.startswith('variant_')
    }

    product: Optional[Product] = db.session.get(Product, product_id)
    if product:
        add_to_cart(product, quantity, variant_options)
    else:
        flash(_("Product not found"), "danger")

    return redirect(request.referrer or url_for('main.product_page', product_id=product_id))


@cart_bp.route("/cart")
@login_required_with_message(redirect_back=True)
def cart() -> str:
    cart_items: List[Cart] = (
        db.session.query(Cart)
        .filter_by(user_id=current_user.id)
        .all()
    )
    subtotal: int = sum(item.price * item.quantity for item in cart_items)
    discount_percentage: float = getattr(current_user, 'discount', 0)
    total_amount: float = subtotal - (subtotal * discount_percentage / 100.0)

    return render_template("cart/cart.html", cart=cart_items, subtotal=subtotal,
                           discount_percentage=discount_percentage, total_amount=total_amount)


@cart_bp.route("/update-cart", methods=["POST"])
@login_required_with_message()
def update_cart_route() -> ResponseValue:
    try:
        quantity: int = int(request.form['quantity'])
        cart_item_id: int = int(request.form['cart_item_id'])
        status: bool = update_cart(cart_item_id, quantity)

        total_items, total_amount, discount_percentage = Cart.cart_info()
        cart_items: int = Cart.total_quantity()

        cart_item: Optional[Cart] = db.session.get(Cart, cart_item_id)
        item_subtotal: float = cart_item.price * cart_item.quantity if cart_item else 0

        return jsonify({
            'subtotal': f'${total_amount:,.2f}',
            'discount': f'-${total_amount * discount_percentage:,.2f}',
            'cart_items': cart_items,
            'cart_total': f'${total_amount * (1 - discount_percentage):,.2f}',
            'item_subtotal': f'${item_subtotal:,.2f}',
            'status': status,
            'message': _('Item quantity updated successfully.') if status else _(
                'Requested quantity exceeds available stock.')
        })
    except ValueError:
        return jsonify({'status': False})


@cart_bp.route("/remove-from-cart/<int:cart_item_id>")
@login_required_with_message()
def remove_from_cart_route(cart_item_id: int) -> ResponseValue:
    if remove_from_cart(cart_item_id):
        flash(_("Item removed from cart."), "success")
    else:
        flash(_("Item not found in cart."), "danger")
    return redirect(url_for('carts.cart'))


@cart_bp.route("/checkout", methods=["GET", "POST"])
@login_required_with_message()
def checkout() -> ResponseValue:
    cart_items: List[Cart] = (
        db.session.query(Cart)
        .filter_by(user_id=current_user.id)
        .all()
    )
    if not cart_items:
        flash(_("Your cart is empty."), "danger")
        return redirect(url_for('carts.cart'))

    if not current_user.addresses:
        flash(_("Please add an address before proceeding to checkout."), "warning")
        return redirect(url_for('profile.profile_info'))

    shipping_methods: List[ShippingMethod] = db.session.query(ShippingMethod).all()
    addresses = current_user.addresses

    subtotal: int = Cart.subtotal()
    shipping_price: int = shipping_methods[0].price if shipping_methods else 0
    total: int = subtotal + shipping_price

    if request.method == "POST":
        return process_payment(cart_items)

    return render_template(
        "cart/checkout.html",
        cart_items=cart_items,
        shipping_methods=shipping_methods,
        addresses=addresses,
        subtotal=subtotal,
        shipping_price=shipping_price,
        total=total
    )


@cart_bp.route("/payment_success")
@login_required_with_message()
def payment_success() -> str | ResponseValue:
    session_id: Optional[str] = request.args.get('session_id')
    if not session_id:
        flash(_("Invalid payment session ID."), "danger")
        return redirect(url_for('carts.checkout'))

    stripe.api_key = AppConfig.STRIPE_SECRET_KEY

    if current_app.config and current_app.config['TESTING']:
        order_id: Optional[int] = request.args.get('order_id', type=int)
        order = db.session.get(Purchase, order_id) if order_id else None
        if order:
            flash(_("Purchase completed. Thank you for shopping with us!"), "success")
            return render_template("cart/success.html", order=order)
        else:
            flash(_("Order not found."), "danger")
            return redirect(url_for('carts.checkout'))

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            return process_successful_payment(session)
        else:
            return handle_unsuccessful_payment()
    except stripe.StripeError as e:
        return handle_stripe_error(e)


@cart_bp.route("/payment_cancel")
@login_required_with_message()
def payment_cancel() -> str:
    flash(_("Payment was cancelled. Please try again or contact support if you continue to have issues."), "warning")
    return render_template("cart/cancel.html")


@cart_bp.route("/order-confirmation")
@login_required_with_message()
def order_confirmation() -> ResponseValue:
    latest_purchase: Optional[Purchase] = (
        db.session.query(Purchase)
        .filter_by(user_id=current_user.id)
        .order_by(Purchase.id.desc())
        .first()
    )

    if not latest_purchase:
        flash(_("No recent purchase found."), "info")
        return redirect(url_for('main.index'))

    total_amount: int = 0
    if latest_purchase:
        delivery_fee: int = latest_purchase.delivery_fee
        total_amount = sum(item.price * item.quantity for item in latest_purchase.items)
        total_amount += delivery_fee

    return render_template("order_confirmation.html",
                           purchase=latest_purchase,
                           total_amount=total_amount)


def init_cart(app: Flask) -> None:
    app.register_blueprint(cart_bp)
