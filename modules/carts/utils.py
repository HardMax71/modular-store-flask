from typing import Optional, List

import stripe
from flask import redirect, url_for, flash
from flask_babel import gettext as _

from modules.db.database import db
from modules.db.models import User, Cart, ShippingMethod


def get_stripe_customer_for_user_by_id(current_user: User):
    # Retrieve or create Stripe customer
    paying_user: Optional[User] = db.session.get(User, current_user.id)
    if not paying_user:
        flash(_("User not found."), "danger")
        return redirect(url_for('carts.checkout'))

    current_user_stripe_customer_id: Optional[str] = paying_user.stripe_customer_id
    if not current_user_stripe_customer_id:
        # customer id is None
        customer = stripe.Customer.create(
            email=current_user.email,
            name=f"{current_user.fname} {current_user.lname}",
            metadata={"user_id": str(current_user.id)}
        )
        current_user.stripe_customer_id = customer.id
        db.session.commit()
    else:
        # customer has stripe id
        customer = stripe.Customer.retrieve(current_user_stripe_customer_id)
        stripe.Customer.modify(
            current_user.stripe_customer_id,
            email=current_user.email,
            name=f"{current_user.fname} {current_user.lname}",
            metadata={"user_id": str(current_user.id)}
        )
    return customer


def create_line_items_for_payment(cart_items: List[Cart], shipping_method: ShippingMethod):
    line_items = [{
        'price_data': {
            'currency': 'usd',
            'product_data': {
                'name': item.goods.samplename,
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
