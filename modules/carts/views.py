import json
import random
from datetime import datetime

import stripe
from flask import Blueprint, jsonify, redirect, request, url_for, flash, render_template
from flask_babel import gettext as _
from flask_login import current_user

from config import AppConfig
from modules.db.database import db
from modules.db.models import Goods, Cart, Discount, UserDiscount, ShippingMethod, Purchase, User
from modules.decorators import login_required_with_message
from modules.email import send_order_confirmation_email
from modules.purchase_history import save_purchase_history

cart_bp = Blueprint('carts', __name__)


@cart_bp.app_template_filter('from_json')
def from_json(value):
    return json.loads(value)


@cart_bp.route("/add-to-cart", methods=["POST"])
@login_required_with_message(redirect_back=True)
def add_to_cart_route():
    quantity = int(request.form.get('quantity', 1))
    goods_id = request.form.get('goods_id')

    # Extract variant options
    variant_options = {}
    for key, value in request.form.items():
        if key.startswith('variant_'):
            variant_name = key.split('variant_')[1]
            variant_options[variant_name] = value

    goods = db.session.get(Goods, goods_id)
    if goods:
        add_to_cart(goods, quantity, variant_options)
    else:
        flash(_("Product not found"), "danger")

    return redirect(request.referrer or url_for('main.goods_page', id=goods_id))


@cart_bp.route("/cart")
@login_required_with_message(redirect_back=True)
def cart():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    subtotal = sum(item.price * item.quantity for item in cart_items)
    discount_percentage = getattr(current_user, 'discount', 0)
    total_amount = subtotal - (subtotal * discount_percentage / 100)

    return render_template("cart/cart.html", cart=cart_items, subtotal=subtotal,
                           discount_percentage=discount_percentage, total_amount=total_amount)


@cart_bp.route("/update-cart", methods=["POST"])
@login_required_with_message()
def update_cart_route():
    try:
        quantity = int(request.form['quantity'])
        cart_item_id = int(request.form['cart_item_id'])
        status = update_cart(cart_item_id, quantity)

        total_items, total_amount, discount_percentage = Cart.cart_info()
        cart_items = Cart.total_quantity()

        cart_item = db.session.get(Cart, cart_item_id)
        item_subtotal = cart_item.price * cart_item.quantity

        return jsonify({
            'subtotal': f'${total_amount:,.2f}',
            'discount': f'-${total_amount * discount_percentage:,.2f}',
            'cart_items': cart_items,
            'cart_total': f'${total_amount * (1 - discount_percentage):,.2f}',
            'item_subtotal': f'${item_subtotal:,.2f}',
            'status': status,
        })
    except ValueError:
        return jsonify({'status': False})


@cart_bp.route("/remove-from-cart/<int:cart_item_id>")
@login_required_with_message()
def remove_from_cart_route(cart_item_id):
    remove_from_cart(cart_item_id)
    flash(_("Item removed from cart."), "success")
    return redirect(url_for('carts.cart'))


@cart_bp.route("/checkout", methods=["GET", "POST"])
@login_required_with_message()
def checkout():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash(_("Your cart is empty."), "danger")
        return redirect(url_for('carts.cart'))

    if not current_user.addresses:
        flash(_("Please add an address before proceeding to checkout."), "warning")
        return redirect(url_for('profile.profile_info'))

    shipping_methods = ShippingMethod.query.all()
    addresses = current_user.addresses

    subtotal = Cart.subtotal()
    shipping_price = shipping_methods[0].price if shipping_methods else 0
    total = subtotal + shipping_price

    if request.method == "POST":
        shipping_address_id = request.form.get("shipping_address")

        shipping_method_id = request.form.get("shipping_method")
        shipping_method = db.session.get(ShippingMethod, shipping_method_id)

        if not shipping_address_id or not shipping_method_id:
            flash(_("Please select both shipping address and shipping method."), "warning")
            return redirect(url_for('carts.checkout'))

        ################ ONLY FOR TEST PURPOSES ###########################
        if AppConfig.STRIPE_SECRET_KEY == 'your_stripe_secret_key':
            # Bypass Stripe payment process for testing/development
            order = save_purchase_history(
                db=db.session,
                cart_items=cart_items,
                original_prices={item.id: item.price for item in cart_items},
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

        # Retrieve or create Stripe customer
        current_user_stripe_customer_id = db.session.get(User, current_user.id).stripe_customer_id
        try:
            customer = stripe.Customer.retrieve(current_user_stripe_customer_id)
        except stripe.error.InvalidRequestError:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=f"{current_user.fname} {current_user.lname}",
                metadata={"user_id": str(current_user.id)}
            )
            current_user.stripe_customer_id = customer.id
            db.session.commit()
        else:
            stripe.Customer.modify(
                current_user.stripe_customer_id,
                email=current_user.email,
                name=f"{current_user.fname} {current_user.lname}",
                metadata={"user_id": str(current_user.id)}
            )

        # Create Stripe Checkout Session
        try:
            # items selected by user
            line_items = [{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': item.goods.samplename,
                    },
                    'unit_amount': int(item.price * 100),
                },
                'quantity': item.quantity,
            } for item in cart_items]

            # Shipping costs
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"Shipping: {shipping_method.name}",
                    },
                    'unit_amount': int(shipping_method.price * 100),
                },
                'quantity': 1,
            })

            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                customer=customer.id,
                client_reference_id=str(current_user.id),
                success_url=url_for('carts.payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=url_for('carts.payment_cancel', _external=True),
                metadata={
                    "shipping_address_id": shipping_address_id,
                    "shipping_method_id": shipping_method_id,
                }
            )
        except Exception as e:
            flash(_("An error occurred while processing your payment: ") + str(e), "danger")
            return redirect(url_for('carts.checkout'))

        return redirect(checkout_session.url, code=303)

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
def payment_success():
    session_id = request.args.get('session_id')
    stripe.api_key = AppConfig.STRIPE_SECRET_KEY

    try:
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status == 'paid':
            cart_items = Cart.query.filter_by(user_id=current_user.id).all()
            original_prices = {item.id: item.price for item in cart_items}

            order = save_purchase_history(
                db=db.session,
                cart_items=cart_items,
                original_prices=original_prices,
                shipping_address_id=session.metadata.get('shipping_address_id'),
                shipping_method_id=session.metadata.get('shipping_method_id'),
                payment_method="stripe",
                payment_id=session.payment_intent
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

    except stripe.error.StripeError as e:
        flash(_("An error occurred while processing your payment: ") + str(e), "danger")
        return redirect(url_for('carts.checkout'))


@cart_bp.route("/payment_cancel")
@login_required_with_message()
def payment_cancel():
    flash(_("Payment was cancelled. Please try again or contact support if you continue to have issues."), "warning")
    return render_template("cart/cancel.html")


@cart_bp.route("/order-confirmation")
@login_required_with_message()
def order_confirmation():
    latest_purchase = Purchase.query.filter_by(user_id=current_user.id).order_by(Purchase.id.desc()).first()
    total_amount = sum(item.price * item.quantity for item in latest_purchase.items)
    return render_template("order_confirmation.html",
                           purchase=latest_purchase,
                           total_amount=total_amount)


# Helper functions
def clear_cart():
    Cart.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()


def update_cart(cart_item_id: int, quantity: int) -> bool:
    cart_item = db.session.get(Cart, cart_item_id)
    if cart_item and cart_item.user_id == current_user.id:
        goods = db.session.get(Goods, cart_item.goods_id)
        stock_difference = quantity - cart_item.quantity

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


def remove_from_cart(cart_item_id):
    cart_item = db.session.get(Cart, cart_item_id)
    if cart_item and cart_item.user_id == current_user.id:
        db.session.delete(cart_item)
        db.session.commit()


def add_to_cart(goods: Goods, quantity: int, variant_options: dict) -> bool:
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

    variant_options_str = json.dumps(variant_options)
    price = goods.current_price  # Using the hybrid property

    cart_item = Cart.query.with_for_update().filter_by(
        user_id=current_user.id,
        goods_id=goods.id,
        variant_options=variant_options_str
    ).first()

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


def apply_discount_code(discount_code):
    discount = Discount.query.filter_by(code=discount_code).first()
    if discount:
        current_date = datetime.now().date()
        if discount.start_date <= current_date <= discount.end_date:
            user_discount = UserDiscount.query.filter_by(user_id=current_user.id,
                                                         discount_id=discount.id).first()
            if user_discount:
                return "already_used"

            cart_items = Cart.query.filter_by(user_id=current_user.id).all()
            for item in cart_items:
                discounted_price = item.price - (item.price * discount.percentage / 100)
                item.price = discounted_price
            new_user_discount = UserDiscount(user_id=current_user.id, discount_id=discount.id)
            db.session.add(new_user_discount)
            db.session.commit()
            return "success"
    return "invalid"


def init_cart(app):
    app.register_blueprint(cart_bp)
