from flask import current_app
from flask import flash
from flask_babel import gettext as _
from flask_login import current_user
from flask_mail import Message

from config import AppConfig
from modules.db.models import User


def send_email(to, subject, body):
    mail_to_send = current_app.extensions['mail']
    msg = Message(subject, recipients=[to])
    msg.body = body
    try:
        mail_to_send.send(msg)
        flash(_("Email sent successfully"), "success")
    except Exception as e:
        flash(_("Error sending email"), "danger")


def send_wishlist_notifications():
    user = current_user
    on_sale_items, back_in_stock_items = User.get_wishlist_notifications()

    if on_sale_items or back_in_stock_items:
        subject = "Wishlist Items Update"
        body = f"Hello {user.username},\n\n"

        if on_sale_items:
            body += "The following wishlist items are now on sale:\n"
            for item in on_sale_items:
                body += f"- {item.samplename}\n"
            body += "\n"

        if back_in_stock_items:
            body += "The following wishlist items are now back in stock:\n"
            for item in back_in_stock_items:
                body += f"- {item.samplename}\n"
            body += "\n"

        body += "Don't miss out on these updates! Visit our store to make your purchase.\n\nBest regards,\nYour Shop Team"

        msg = Message(subject, recipients=[user.email], body=body)
        try:
            current_app.extensions['mail'].send(msg)
        except Exception as e:
            print(f"Error sending wishlist notifications: {e}")


def send_order_confirmation_email(email, name):
    msg = Message('Order Confirmation', sender=AppConfig.CONTACT_EMAIL, recipients=[email])
    msg.body = f"Dear {name},\n\nThank you for your purchase. Your order has been received and will be processed shortly.\n\nBest regards,\nThe Store Team"
    try:
        current_app.extensions['mail'].send(msg)
        flash(_("Order confirmation email sent successfully"), "success")
    except Exception as e:
        flash(_("Error sending order confirmation email"), "danger")
