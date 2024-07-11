from smtplib import SMTPException
from typing import List

from flask import current_app, flash
from flask_babel import gettext as _
from flask_login import current_user
from flask_mail import Message, BadHeaderError

from config import AppConfig
from modules.db.models import User, Goods


def send_email(to: str, subject: str, body: str) -> None:
    """
    Send an email.

    :param to: Recipient email address
    :param subject: Subject of the email
    :param body: Body of the email
    """
    mail_to_send = current_app.extensions['mail']
    msg = Message(subject, recipients=[to])
    msg.body = body
    try:
        mail_to_send.send(msg)
        flash(_("Email sent successfully"), "success")
    except BadHeaderError:
        flash(_("Invalid email header"), "danger")
    except SMTPException as e:
        flash(_("SMTP error occurred: {}").format(str(e)), "danger")
    except Exception as e:
        flash(_("Unexpected error sending email: {}").format(str(e)), "danger")


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


def create_wishlist_message(on_sale_items: List[Goods], back_in_stock_items: List[Goods]) -> str:
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
        flash(_("Invalid email header in wishlist notification"), "danger")
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
        flash(_("Invalid email header in order confirmation"), "danger")
    except SMTPException as e:
        flash(_("SMTP error sending order confirmation: {}").format(str(e)), "danger")
    except Exception as e:
        flash(_("Unexpected error sending order confirmation: {}").format(str(e)), "danger")
