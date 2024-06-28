import json
import random
from datetime import datetime

import stripe
from flask import Blueprint, jsonify, redirect, request, url_for, flash, render_template
from flask_babel import gettext as _
from flask_login import current_user

from config import AppConfig
from modules.db.database import db
from modules.db.models import Goods, Cart, Discount, UserDiscount, ShippingMethod, Purchase
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

    goods = Goods.query.get(goods_id)
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

        cart_item = Cart.query.get(cart_item_id)
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
        shipping_address_id = request.form.get("shipping_address", int)
        shipping_method_id = request.form.get("shipping_method", int)
        payment_method = request.form.get("payment_method")
        stripe.api_key = AppConfig.STRIPE_SECRET_KEY

        try:
            # Stripe payment processing code here (currently commented out)
            # token = stripe.Token.create(
            #     card={
            #         "number": request.form.get("card_number"),
            #         "exp_month": request.form.get("exp_month"),
            #         "exp_year": request.form.get("exp_year"),
            #         "cvc": request.form.get("cvc")
            #     },
            # )
            #
            # charge = stripe.Charge.create(
            #     amount=int(sum(item.price * item.quantity for item in cart_items) + shipping_method.price) * 100,
            #     currency="usd",
            #     source=token.id,
            #     description="Purchase"
            # )

            original_prices = {item.id: item.price for item in cart_items}
            save_purchase_history(db=db.session,
                                  cart_items=cart_items,
                                  original_prices=original_prices,
                                  shipping_address_id=shipping_address_id,
                                  shipping_method_id=shipping_method_id,
                                  payment_method=payment_method,
                                  payment_id=random.randint(100000, 999999))  # should be charge.id
            clear_cart()
            current_user.discount = 0
            db.session.commit()

            send_order_confirmation_email(current_user.email, current_user.fname)
            flash(_("Purchase completed. Thank you for shopping with us!"), "success")
            return redirect(url_for('carts.order_confirmation'))

        except stripe.error.CardError as e:
            flash(_("Payment failed") + ":" + e.user_message, "danger")

    return render_template("cart/checkout.html",
                           cart_items=cart_items,
                           shipping_methods=shipping_methods,
                           addresses=addresses,
                           subtotal=subtotal,
                           shipping_price=shipping_price,
                           total=total)


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
    cart_item = Cart.query.get(cart_item_id)
    if cart_item and cart_item.user_id == current_user.id:
        goods = Goods.query.get(cart_item.goods_id)
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
    cart_item = Cart.query.get(cart_item_id)
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
