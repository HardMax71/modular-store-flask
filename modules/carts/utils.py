import json
import random
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any

import stripe
from flask import redirect, request, url_for, flash, current_app, render_template
from flask.typing import ResponseValue
from flask_babel import gettext as _
from flask_login import current_user

from config import AppConfig
from modules.db.database import db
from modules.db.models import Product, Cart, Discount, UserDiscount, ShippingMethod, Purchase
from modules.db.models import User
from modules.email import send_order_confirmation_email
from modules.purchase_history import save_purchase_history


def process_payment(cart_items: List[Cart]) -> ResponseValue:
    shipping_info = get_shipping_info()
    if not shipping_info:
        return redirect(url_for('carts.checkout'))

    shipping_address_id, shipping_method = shipping_info

    if current_app.config and current_app.config['TESTING']:
        return process_test_payment(cart_items, shipping_address_id, shipping_method.id)

    return process_stripe_payment(cart_items, shipping_address_id, shipping_method)


def get_shipping_info() -> Optional[Tuple[int, ShippingMethod]]:
    shipping_address_form_id: Optional[str] = request.form.get("shipping_address", type=str, default=None)
    shipping_method_form_id: Optional[str] = request.form.get("shipping_method", type=str, default=None)

    if not shipping_address_form_id or not shipping_method_form_id:
        flash(_("Please select both shipping address and shipping method."), "warning")
        return None

    shipping_address_id = int(shipping_address_form_id)
    shipping_method_id = int(shipping_method_form_id)

    shipping_method: Optional[ShippingMethod] = db.session.get(ShippingMethod, shipping_method_id)
    if not shipping_method:
        flash(_("Invalid shipping method."), "danger")
        return None

    return shipping_address_id, shipping_method


def process_test_payment(cart_items: List[Cart], shipping_address_id: int, shipping_method_id: int) -> ResponseValue:
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


def process_stripe_payment(cart_items: List[Cart], shipping_address_id: int,
                           shipping_method: ShippingMethod) -> ResponseValue:
    stripe.api_key = AppConfig.STRIPE_SECRET_KEY
    customer: stripe.Customer = get_stripe_acc_for_customer_by_stripe_customer_id(current_user)

    try:
        line_items = create_line_items_for_payment(cart_items, shipping_method)
        checkout_session = create_stripe_checkout_session(customer.id, line_items, shipping_address_id,
                                                          shipping_method.id)
    except Exception as e:
        flash(_("An error occurred while processing your payment: ") + str(e), "danger")
        return redirect(url_for('carts.checkout'))

    return redirect(checkout_session.url or url_for('carts.checkout'), code=303)


def create_stripe_checkout_session(customer_id: str, line_items: List[Dict[str, Any]], shipping_address_id: int,
                                   shipping_method_id: int) -> stripe.checkout.Session:
    return stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,  # type: ignore
        mode='payment',
        customer=customer_id,
        client_reference_id=str(current_user.id),
        success_url=url_for('carts.payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=url_for('carts.payment_cancel', _external=True),
        metadata={
            "shipping_address_id": str(shipping_address_id),
            "shipping_method_id": str(shipping_method_id),
        }
    )


def get_stripe_acc_for_customer_by_stripe_customer_id(user: User) -> stripe.Customer:
    current_user_stripe_customer_id: Optional[str] = user.stripe_customer_id
    if not current_user_stripe_customer_id:
        # customer id is None
        customer = stripe.Customer.create(
            email=user.email or "no email specified",
            name=f"{user.fname} {user.lname}",
            metadata={"user_id": str(user.id)}
        )
        user.stripe_customer_id = customer.id
        db.session.commit()
    else:
        # customer has stripe id
        customer = stripe.Customer.retrieve(current_user_stripe_customer_id)
        stripe.Customer.modify(
            user.stripe_customer_id,
            email=user.email or "no email specified",
            name=f"{user.fname} {user.lname}",
            metadata={"user_id": str(user.id)}
        )
    return customer


def create_line_items_for_payment(cart_items: List[Cart], shipping_method: ShippingMethod) -> List[Dict[str, Any]]:
    line_items = [{
        'price_data': {
            'currency': 'usd',
            'product_data': {
                'name': item.product.samplename,
            },
            'unit_amount': item.price,
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
            'unit_amount': shipping_method.price,
        },
        'quantity': 1,
    })
    return line_items


# Helper functions
def clear_cart() -> None:
    db.session.query(Cart).filter_by(user_id=current_user.id).delete()
    db.session.commit()


def update_cart(cart_item_id: int, quantity: int) -> bool:
    cart_item: Optional[Cart] = db.session.get(Cart, cart_item_id)
    if not (cart_item and cart_item.user_id == current_user.id):
        return False

    if product := db.session.get(Product, cart_item.product_id):
        stock_difference: int = quantity - cart_item.quantity

        if product.stock >= stock_difference:
            if quantity > 0:
                cart_item.quantity = quantity
                product.stock -= stock_difference
            else:
                remove_from_cart(cart_item_id)
                product.stock += cart_item.quantity

            db.session.commit()
            return True
        else:
            flash(_("Not enough stock available for this product."), "danger")

    return False


def remove_from_cart(cart_item_id: int) -> bool:
    cart_item: Optional[Cart] = db.session.get(Cart, cart_item_id)
    if not (cart_item and cart_item.user_id == current_user.id):
        return False

    db.session.delete(cart_item)
    db.session.commit()
    return True


def add_to_cart(product: Product, quantity: int, variant_options: Dict[str, str]) -> bool:
    """
    Add an item to the user's cart or update its quantity if it already exists.

    :param product: The Product object to add to the cart
    :param quantity: The quantity to add
    :param variant_options: A dictionary of variant options
    :return: True if the item was added successfully, False otherwise
    """
    if quantity <= 0:
        flash(_("Invalid quantity. Please select a positive number."), "danger")
        return False

    if product.stock < quantity:
        flash(_("Not enough stock available for this product."), "danger")
        return False

    variant_options_str: str = json.dumps(variant_options)
    price: int = product.current_price

    cart_item: Optional[Cart] = (
        db.session.query(Cart)
        .with_for_update()
        .filter_by(user_id=current_user.id, product_id=product.id, variant_options=variant_options_str)
        .first()
    )

    if cart_item:
        cart_item.quantity += quantity
        cart_item.price = price  # Update price in case it has changed
    else:
        cart_item = Cart(
            user_id=current_user.id,
            product_id=product.id,
            quantity=quantity,
            price=price,
            variant_options=variant_options_str
        )
        db.session.add(cart_item)

    product.stock -= quantity
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


def process_successful_payment(session: stripe.checkout.Session) -> str:
    cart_items = db.session.query(Cart).filter_by(user_id=current_user.id).all()
    order = create_order(session, cart_items)
    finalize_order()
    return render_success_page(order)


def create_order(session: stripe.checkout.Session, cart_items: List[Cart]) -> Purchase:
    return save_purchase_history(
        db_session=db.session,
        cart_items=cart_items,
        shipping_address_id=get_metadata_value(session, 'shipping_address_id'),
        shipping_method_id=get_metadata_value(session, 'shipping_method_id'),
        payment_method="stripe",
        payment_id=str(session.payment_intent)
    )


def get_metadata_value(session: stripe.checkout.Session, key: str) -> int:
    return int(session.metadata.get(key, '-1')) if session.metadata else -1


def finalize_order() -> None:
    clear_cart()
    current_user.discount = 0
    db.session.commit()
    send_order_confirmation_email(current_user.email, current_user.fname)


def render_success_page(order: Purchase) -> str:
    flash(_("Purchase completed. Thank you for shopping with us!"), "success")
    return render_template("cart/success.html", order=order)


def handle_unsuccessful_payment() -> ResponseValue:
    flash(_("Payment was not successful. Please try again."), "danger")
    return redirect(url_for('carts.checkout'))


def handle_stripe_error(e: stripe.StripeError) -> ResponseValue:
    flash(_("An error occurred while processing your payment: ") + str(e), "danger")
    return redirect(url_for('carts.checkout'))
