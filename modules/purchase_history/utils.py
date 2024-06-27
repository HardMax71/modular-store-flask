import datetime
from typing import List, Dict, Optional

from flask_login import current_user
from sqlalchemy.orm import Session

from modules.db.models import Purchase, PurchaseItem, ShippingAddress, Address, ShippingMethod
from modules.email import send_email


def save_purchase_history(
        db: Session,
        cart_items: List[PurchaseItem],
        original_prices: Dict[int, float],
        shipping_address_id: int,
        shipping_method_id: int,
        payment_method: str,
        payment_id: int
) -> None:
    if not cart_items:
        return

    user_id = current_user.id
    subtotal = calculate_subtotal(cart_items, original_prices)
    discount_percentage = getattr(current_user, 'discount', 0)
    discount_amount = calculate_discount_amount(subtotal, discount_percentage)
    shipping_method = get_shipping_method_by_id(db, shipping_method_id)
    delivery_fee = calculate_delivery_fee(shipping_method)
    total_price = calculate_total_price(subtotal, discount_amount, delivery_fee)
    tracking_number = generate_tracking_number()
    shipping_address = get_address_by_id(db, shipping_address_id)

    if shipping_address is None:
        raise ValueError("Invalid shipping address ID")

    new_purchase = Purchase(
        user_id=user_id,
        date=datetime.datetime.now(),
        total_price=total_price,
        discount_amount=discount_amount,
        delivery_fee=delivery_fee,
        status="Completed",
        tracking_number=tracking_number,
        shipping_method=shipping_method.name if shipping_method else None,
        payment_method=payment_method,
        payment_id=payment_id
    )

    db.add(new_purchase)
    db.flush()

    new_shipping_address = ShippingAddress(
        purchase_id=new_purchase.id,
        address_line1=shipping_address.address_line1,
        address_line2=shipping_address.address_line2,
        city=shipping_address.city,
        state=shipping_address.state,
        zip_code=shipping_address.zip_code,
        country=shipping_address.country
    )
    db.add(new_shipping_address)

    create_purchase_items(db, new_purchase.id, cart_items, original_prices)

    db.commit()
    Purchase.update_stock(new_purchase)
    send_order_confirmation_email(current_user.email)


def get_purchase_history(db: Session) -> List[Purchase]:
    user_id = current_user.id
    purchases = db.query(Purchase).filter_by(user_id=user_id).order_by(Purchase.date.desc()).all()
    for purchase in purchases:
        purchase.items_subtotal = calculate_items_subtotal(purchase.items)
    return purchases


def get_purchase_by_id(db: Session, purchase_id: int) -> Optional[Purchase]:
    return db.query(Purchase).get(purchase_id)


def get_shipping_method_by_id(db: Session, shipping_method_id: int) -> Optional[ShippingMethod]:
    return db.query(ShippingMethod).get(shipping_method_id)


def get_address_by_id(db: Session, address_id: int) -> Optional[Address]:
    return db.query(Address).get(address_id)


def calculate_subtotal(cart_items: List[PurchaseItem], original_prices: Dict[int, float]) -> float:
    return sum(original_prices[item.id] * item.quantity for item in cart_items)


def calculate_discount_amount(subtotal: float, discount_percentage: float) -> float:
    return subtotal * (discount_percentage / 100)


def calculate_delivery_fee(shipping_method: Optional[ShippingMethod]) -> float:
    return shipping_method.price if shipping_method else 0.0


def calculate_total_price(subtotal: float, discount_amount: float, delivery_fee: float) -> float:
    return subtotal - discount_amount + delivery_fee


def generate_tracking_number() -> str:
    timestamp = str(datetime.datetime.now().timestamp()).replace('.', '')[:10]
    return f'TRACK{timestamp}'


def create_purchase_items(
        db: Session,
        purchase_id: int,
        cart_items: List[PurchaseItem],
        original_prices: Dict[int, float]
) -> None:
    for item in cart_items:
        new_purchase_item = PurchaseItem(
            purchase_id=purchase_id,
            goods_id=item.goods_id,
            quantity=item.quantity,
            price=original_prices[item.id]
        )
        db.add(new_purchase_item)


def calculate_items_subtotal(items: List[PurchaseItem]) -> float:
    return sum(item.quantity * item.price for item in items)


def send_order_confirmation_email(email: str):
    send_email(email,
               'Order Confirmation',
               'Thank you for your order! Your order is being processed.')
