import os
from smtplib import SMTPException
from typing import List, Optional

from flask import current_app
from flask import flash
from flask_babel import gettext as _
from flask_login import current_user
from flask_mail import BadHeaderError
from flask_mail import Message

from config import AppConfig
from modules.db.models import User, Product


def send_email(recipient: str, subject: str, body: str, attachments: Optional[list[str]] = None) -> None:
    mail = current_app.extensions['mail']
    msg = Message(subject, recipients=[recipient])
    msg.body = body

    if attachments:
        for attachment in attachments:
            with current_app.open_resource(attachment) as fp:
                msg.attach(os.path.basename(attachment), "application/octet-stream", fp.read())

    try:
        mail.send(msg)
        for attachment in attachments or []:
            os.remove(attachment)  # Clean up uploaded files after sending
    except Exception as e:
        current_app.logger.error(f"Error sending email: {str(e)}")
        raise


def send_wishlist_notifications() -> None:
    """
    Send notifications for wishlist items that are on sale or back in stock.
    """
    user: User = current_user
    on_sale_items, back_in_stock_items = User.get_wishlist_notifications()

    if on_sale_items or back_in_stock_items:
        subject: str = _("Wishlist Items Update")
        body: str = f"Hello {user.username},\n\n"

        body += create_wishlist_message(on_sale_items, back_in_stock_items)

        body += _("Don't miss out on these updates! Visit our store to make your purchase.\n\nBest regards,"
                  "\nYour Shop Team")

        msg = Message(subject, recipients=[user.email], body=body)
        send_wishlist_email(msg)


def create_wishlist_message(on_sale_items: List[Product], back_in_stock_items: List[Product]) -> str:
    """
    Create the message body for wishlist notifications.

    :param on_sale_items: List of items on sale
    :param back_in_stock_items: List of items back in stock
    :return: Formatted message string
    """
    message: str = ""
    if on_sale_items:
        message += _("The following wishlist items are now on sale:\n")
        message += "\n".join(f"- {item.samplename}" for item in on_sale_items)
        message += "\n\n"

    if back_in_stock_items:
        message += _("The following wishlist items are now back in stock:\n")
        message += "\n".join(f"- {item.samplename}" for item in back_in_stock_items)
        message += "\n\n"

    return message


def send_wishlist_email(msg: Message) -> None:
    """
    Send the wishlist notification email.

    :param msg: Message object to be sent
    """
    try:
        current_app.extensions['mail'].send(msg)
        flash(_("Wishlist notifications sent successfully."), "success")
    except BadHeaderError:
        flash(_("Invalid email header"), "danger")
    except SMTPException as e:
        flash(_("SMTP error sending wishlist notification: {}").format(str(e)), "danger")
    except Exception as e:
        flash(_("Unexpected error sending wishlist notification: {}").format(str(e)), "danger")


def send_order_confirmation_email(email: str, name: str) -> None:
    """
    Send an order confirmation email.

    :param email: Recipient email address
    :param name: Recipient name
    """
    msg = Message(
        _('Order Confirmation'),
        sender=AppConfig.CONTACT_EMAIL,
        recipients=[email]
    )
    msg.body = _(
        "Dear {name},\n\nThank you for your purchase. Your order has been received and will be processed "
        "shortly.\n\nBest regards,\nThe Store Team"
    ).format(name=name)
    try:
        current_app.extensions['mail'].send(msg)
        flash(_("Order confirmation email sent successfully"), "success")
    except BadHeaderError:
        flash(_("Invalid email header"), "danger")
    except SMTPException as e:
        flash(_("SMTP error sending order confirmation: {}").format(str(e)), "danger")
    except Exception as e:
        flash(_("Unexpected error sending order confirmation: {}").format(str(e)), "danger")
