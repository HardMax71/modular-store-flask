import json
import random
from datetime import datetime
from typing import Optional, Dict, Any, List

import stripe
from flask import Blueprint, jsonify, redirect, request, url_for, flash, render_template, Flask
from flask.typing import ResponseValue
from flask_babel import gettext as _
from flask_login import current_user

from config import AppConfig
from modules.carts.utils import get_stripe_customer_for_user_by_id, create_line_items_for_payment
from modules.db.database import db
from modules.db.models import Goods, Cart, Discount, UserDiscount, ShippingMethod, Purchase
from modules.decorators import login_required_with_message
from modules.email import send_order_confirmation_email
from modules.purchase_history import save_purchase_history

cart_bp = Blueprint('carts', __name__)


@cart_bp.app_template_filter('from_json')
def from_json(value: str) -> Any:
    return json.loads(value)


@cart_bp.route("/add-to-cart", methods=["POST"])
@login_required_with_message(redirect_back=True)
def add_to_cart_route() -> ResponseValue:
    quantity: int = request.form.get('quantity', type=int, default=1)
    goods_id: Optional[int] = request.form.get('goods_id', type=int)

    variant_options: Dict[str, str] = {
        key.split('variant_')[1]: value
        for key, value in request.form.items() if key.startswith('variant_')
    }

    goods: Optional[Goods] = db.session.get(Goods, goods_id)
    if goods:
        add_to_cart(goods, quantity, variant_options)
    else:
        flash(_("Product not found"), "danger")

    return redirect(request.referrer or url_for('main.goods_page', id=goods_id))


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


def process_payment(cart_items: List[Cart]) -> ResponseValue:  # TODO: Refactor this function
    shipping_address_form_id: Optional[str] = request.form.get("shipping_address", type=str, default=None)
    shipping_method_form_id: Optional[str] = request.form.get("shipping_method", type=str, default=None)

    if not shipping_address_form_id or not shipping_method_form_id:
        flash(_("Please select both shipping address and shipping method."), "warning")
        return redirect(url_for('carts.checkout'))

    shipping_address_id = int(shipping_address_form_id)
    shipping_method_id = int(shipping_method_form_id)

    shipping_method: Optional[ShippingMethod] = db.session.get(ShippingMethod, shipping_method_id)
    if not shipping_method:
        flash(_("Invalid shipping method."), "danger")
        return redirect(url_for('carts.checkout'))

    ################ ONLY FOR TEST PURPOSES ###########################
    if AppConfig.STRIPE_SECRET_KEY == 'your_stripe_secret_key':
        # Bypass Stripe payment process for testing/development
        order = save_purchase_history(
            db_session=db.session,
            cart_items=cart_items,
            shipping_address_id=shipping_address_id,
            shipping_method_id=shipping_method_id,
            payment_method="test_payment",
            payment_id="test_" + str(random.randint(10000, 99999))
        )

        clear_cart()
        current_user.discount = 0
        db.session.commit()

        send_order_confirmation_email(current_user.email, current_user.fname)
        flash(_("Test purchase completed. Thank you for shopping with us!"), "success")
        return redirect(url_for('carts.payment_success', order_id=order.id))
    ################ ONLY FOR TEST PURPOSES ###########################

    # More details on Stripe: https://docs.stripe.com/testing
    stripe.api_key = AppConfig.STRIPE_SECRET_KEY
    customer: stripe.Customer = get_stripe_customer_for_user_by_id(current_user)

    # Create Stripe Checkout Session
    try:
        # items selected by user
        line_items = create_line_items_for_payment(cart_items, shipping_method)

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            customer=customer.id,
            client_reference_id=str(current_user.id),
            success_url=url_for('carts.payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('carts.payment_cancel', _external=True),
            metadata={
                "shipping_address_id": str(shipping_address_id),
                "shipping_method_id": str(shipping_method_id),
            }
        )
    except Exception as e:
        flash(_("An error occurred while processing your payment: ") + str(e), "danger")
        return redirect(url_for('carts.checkout'))

    return redirect(checkout_session.url or url_for('carts.checkout'), code=303)


@cart_bp.route("/payment_success")
@login_required_with_message()
def payment_success() -> str | ResponseValue:
    session_id: Optional[str] = request.args.get('session_id')
    if not session_id:
        flash(_("Invalid payment session ID."), "danger")
        return redirect(url_for('carts.checkout'))

    stripe.api_key = AppConfig.STRIPE_SECRET_KEY

    # ONLY FOR TEST PURPOSES
    if AppConfig.STRIPE_SECRET_KEY == 'your_stripe_secret_key':
        order_id: Optional[int] = request.args.get('order_id', type=int)
        flash(_("Purchase completed. Thank you for shopping with us!"), "success")
        return render_template("cart/success.html", order=db.session.get(Purchase, order_id))
    # ONLY FOR TEST PURPOSES

    try:
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status == 'paid':
            cart_items = (
                db.session.query(Cart)
                .filter_by(user_id=current_user.id)
                .all()
            )

            order = save_purchase_history(
                db_session=db.session,
                cart_items=cart_items,  # Pass the converted purchase_items here
                shipping_address_id=int(session.metadata.get('shipping_address_id', '-1')) if session.metadata else -1,
                shipping_method_id=int(session.metadata.get('shipping_method_id', '-1')) if session.metadata else -1,
                payment_method="stripe",
                payment_id=str(session.payment_intent)
            )

            clear_cart()
            current_user.discount = 0
            db.session.commit()

            send_order_confirmation_email(current_user.email, current_user.fname)
            flash(_("Purchase completed. Thank you for shopping with us!"), "success")
            return render_template("cart/success.html", order=order)
        else:
            flash(_("Payment was not successful. Please try again."), "danger")
            return redirect(url_for('carts.checkout'))

    except stripe.StripeError as e:
        flash(_("An error occurred while processing your payment: ") + str(e), "danger")
        return redirect(url_for('carts.checkout'))


@cart_bp.route("/payment_cancel")
@login_required_with_message()
def payment_cancel() -> str:
    flash(_("Payment was cancelled. Please try again or contact support if you continue to have issues."), "warning")
    return render_template("cart/cancel.html")


@cart_bp.route("/order-confirmation")
@login_required_with_message()
def order_confirmation() -> str:
    latest_purchase: Optional[Purchase] = (
        db.session.query(Purchase)
        .filter_by(user_id=current_user.id)
        .order_by(Purchase.id.desc())
        .first()
    )

    total_amount: int = 0
    if latest_purchase:
        delivery_fee: int = latest_purchase.delivery_fee
        total_amount = sum(item.price * item.quantity for item in latest_purchase.items)
        total_amount += delivery_fee

    return render_template("order_confirmation.html",
                           purchase=latest_purchase,
                           total_amount=total_amount)


# Helper functions
def clear_cart() -> None:
    db.session.query(Cart).filter_by(user_id=current_user.id).delete()
    db.session.commit()


def update_cart(cart_item_id: int, quantity: int) -> bool:
    cart_item: Optional[Cart] = db.session.get(Cart, cart_item_id)
    if cart_item and cart_item.user_id == current_user.id:
        goods: Optional[Goods] = db.session.get(Goods, cart_item.goods_id)
        if goods:
            stock_difference: int = quantity - cart_item.quantity

            if goods.stock >= stock_difference:
                if quantity > 0:
                    cart_item.quantity = quantity
                    goods.stock -= stock_difference
                else:
                    remove_from_cart(cart_item_id)
                    goods.stock += cart_item.quantity

                db.session.commit()
                return True
            else:
                flash(_("Not enough stock available for this product."), "danger")

    return False


def remove_from_cart(cart_item_id: int) -> bool:
    cart_item: Optional[Cart] = db.session.get(Cart, cart_item_id)
    if cart_item and cart_item.user_id == current_user.id:
        db.session.delete(cart_item)
        db.session.commit()
        return True
    return False


def add_to_cart(goods: Goods, quantity: int, variant_options: Dict[str, str]) -> bool:
    """
    Add an item to the user's cart or update its quantity if it already exists.

    :param goods: The Goods object to add to the cart
    :param quantity: The quantity to add
    :param variant_options: A dictionary of variant options
    :return: True if the item was added successfully, False otherwise
    """
    if quantity <= 0:
        flash(_("Invalid quantity. Please select a positive number."), "danger")
        return False

    if goods.stock < quantity:
        flash(_("Not enough stock available for this product."), "danger")
        return False

    variant_options_str: str = json.dumps(variant_options)
    price: int = goods.current_price

    cart_item: Optional[Cart] = (
        db.session.query(Cart)
        .with_for_update()
        .filter_by(user_id=current_user.id, goods_id=goods.id, variant_options=variant_options_str)
        .first()
    )

    if cart_item:
        cart_item.quantity += quantity
        cart_item.price = price  # Update price in case it has changed
    else:
        cart_item = Cart(
            user_id=current_user.id,
            goods_id=goods.id,
            quantity=quantity,
            price=price,
            variant_options=variant_options_str
        )
        db.session.add(cart_item)

    goods.stock -= quantity
    db.session.commit()
    flash(_("Item added to cart."), "success")
    return True


def apply_discount_code(discount_code: str) -> str:
    discount: Optional[Discount] = (
        db.session.query(Discount)
        .filter_by(code=discount_code)
        .first()
    )
    if discount:
        current_date = datetime.now().date()
        if discount.start_date <= current_date <= discount.end_date:  # type: ignore
            user_discount: Optional[UserDiscount] = (
                db.session.query(UserDiscount)
                .filter_by(user_id=current_user.id, discount_id=discount.id)
                .first()
            )
            if user_discount:
                return "already_used"

            cart_items: List[Cart] = (
                db.session.query(Cart)
                .filter_by(user_id=current_user.id)
                .all()
            )
            for item in cart_items:
                discounted_price = int(
                    item.price - (item.price * discount.percentage / 100.0))  # percentage: int in [0..100]
                item.price = discounted_price
            new_user_discount = UserDiscount(user_id=current_user.id, discount_id=discount.id)
            db.session.add(new_user_discount)
            db.session.commit()
            return "success"
    return "invalid"


def init_cart(app: Flask) -> None:
    app.register_blueprint(cart_bp)
