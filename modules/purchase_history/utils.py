import datetime
from typing import List, Optional

from flask_login import current_user
from sqlalchemy.orm import scoped_session

from modules.db.models import Purchase, PurchaseItem, ShippingAddress, Address, ShippingMethod, Cart
from modules.email import send_email


def save_purchase_history(
        db_session: scoped_session,
        cart_items: List[Cart],
        shipping_address_id: int,
        shipping_method_id: int,
        payment_method: str,
        payment_id: str
) -> Purchase:
    if not cart_items:
        raise ValueError("No cart items!")

    user_id = current_user.id
    subtotal = sum(item.price * item.quantity for item in cart_items)
    discount_percentage = getattr(current_user, 'discount', 0)
    discount_amount = calculate_discount_amount(subtotal, discount_percentage)
    shipping_method = db_session.get(ShippingMethod, shipping_method_id)
    delivery_fee = calculate_delivery_fee(shipping_method)
    total_price = calculate_total_price(subtotal, discount_amount, delivery_fee)
    tracking_number = generate_tracking_number()
    shipping_address = db_session.get(Address, shipping_address_id)

    if shipping_address is None:
        raise ValueError("Invalid shipping address ID")

    new_purchase = Purchase(
        user_id=user_id,
        date=datetime.datetime.now(),
        total_price=total_price,
        discount_amount=discount_amount,
        delivery_fee=delivery_fee,
        status="Pending",  # changed from completed to pending, only admin may change status to completed
        tracking_number=tracking_number,
        shipping_method=shipping_method.name if shipping_method else None,
        payment_method=payment_method,
        payment_id=payment_id
    )

    db_session.add(new_purchase)
    db_session.flush()

    new_shipping_address = ShippingAddress(
        purchase_id=new_purchase.id,
        address_line1=shipping_address.address_line1,
        address_line2=shipping_address.address_line2,
        city=shipping_address.city,
        state=shipping_address.state,
        zip_code=shipping_address.zip_code,
        country=shipping_address.country
    )
    db_session.add(new_shipping_address)
    db_session.flush()

    create_purchase_items(db_session=db_session, purchase_id=new_purchase.id, cart_items=cart_items)

    db_session.commit()
    Purchase.update_stock(new_purchase)
    send_order_confirmation_email(current_user.email)

    return new_purchase


def calculate_discount_amount(subtotal: float, discount_percentage: float) -> float:
    return subtotal * (discount_percentage / 100)


def calculate_delivery_fee(shipping_method: Optional[ShippingMethod]) -> int:
    return shipping_method.price if shipping_method else 0


def calculate_total_price(subtotal: int, discount_amount: float, delivery_fee: int) -> float:
    return subtotal - discount_amount + delivery_fee


def generate_tracking_number() -> str:
    timestamp = str(datetime.datetime.now().timestamp()).replace('.', '')[:10]
    return f'TRACK{timestamp}'


def create_purchase_items(
        db_session: scoped_session,
        purchase_id: int,
        cart_items: List[Cart]
) -> None:
    for item in cart_items:
        new_purchase_item = PurchaseItem(
            purchase_id=purchase_id,
            goods_id=item.goods_id,
            quantity=item.quantity,
            price=item.price
        )
        db_session.add(new_purchase_item)
    db_session.flush()


def send_order_confirmation_email(email: str) -> None:
    send_email(email,
               'Order Confirmation',
               'Thank you for your order! Your order is being processed.')
