# //modular_store_backend/modules/profile/utils.py
import os
from typing import Callable, Optional

import phonenumbers
from flask import request, flash, redirect, url_for, current_app
from flask_babel import gettext as _
from flask_login import current_user
from phonenumbers import NumberParseException
from werkzeug import Response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from modular_store_backend.modules.db.database import db
from modular_store_backend.modules.db.models import User, SocialAccount


def handle_profile_update() -> None:
    """
    Handle various profile update actions based on the submitted form.
    This function delegates to specific handlers for each type of update.
    """
    form_actions: dict[str, Callable[[], any]] = {
        'change_email': handle_change_email,
        'change_password': handle_change_password,
        'change_phone': handle_change_phone,
        'update_profile': handle_update_profile,
        'change_language': handle_change_language,
        'update_notification_settings': handle_update_notification_settings
    }
    for action, handler in form_actions.items():
        if action in request.form:
            handler()
            break
    else:
        flash(_('Invalid request.'), 'danger')


def handle_change_email() -> None:
    """
    Handle the change of user's email address.
    Validates the new email and updates it if it's not already in use.
    """
    new_email: str = request.form['email'].strip()
    if new_email and new_email != current_user.email:
        existing_user: Optional[User] = db.session.query(User).filter(User.email == new_email,
                                                                      User.id != current_user.id).first()
        if not existing_user:
            current_user.email = new_email
            db.session.commit()
            flash(_('Email changed successfully.'), 'success')
        else:
            flash(_('This email is already in use.'), 'warning')
    else:
        flash(_('New email is either empty or same as previous one.'), 'warning')


def handle_change_password() -> bool:
    """
    Handle the change of user's password.
    Verifies the current password and updates to the new password if confirmed.

    Returns:
        bool: True if password was successfully changed, False otherwise.
    """
    current_password: str = request.form['current_password']
    new_password: str = request.form['new_password']
    confirm_password: str = request.form['confirm_password']
    if check_password_hash(current_user.password, current_password):
        if new_password and new_password == confirm_password:
            current_user.password = generate_password_hash(new_password)
            db.session.commit()
            flash(_('Password changed successfully.'), 'success')
            return True
        else:
            flash(_('The new password and confirmation do not match.'), 'danger')
    else:
        flash(_('Incorrect current password.'), 'danger')
    return False


def handle_change_phone() -> bool:
    """
    Handle the change of user's phone number.
    Validates the new phone number format before updating.

    Returns:
        bool: True if phone number was successfully changed, False otherwise.
    """
    new_phone: str = request.form['phone'].strip()
    if new_phone and new_phone != current_user.phone:
        try:
            phone_number: phonenumbers.PhoneNumber = phonenumbers.parse(new_phone, None)
            if not phonenumbers.is_valid_number(phone_number):
                raise NumberParseException(0, "Invalid phone number")

            current_user.phone = new_phone
            db.session.commit()
            flash(_('Phone number successfully changed.'), 'success')
            return True
        except NumberParseException:
            flash(_('Invalid phone number format.'), 'danger')
            return False
    else:
        flash(_('The new phone number matches the current one or is empty.'), 'warning')
        return False


def validate_phone(phone: str) -> bool:
    try:
        phone_number: phonenumbers.PhoneNumber = phonenumbers.parse(phone, None)
        if not phonenumbers.is_valid_number(phone_number):
            raise NumberParseException(0, "Invalid phone number")
        return True
    except NumberParseException:
        return False


def handle_update_profile() -> None:
    """
    Handle updating various user profile details including name, phone, and profile picture.
    Validates the phone number format before updating.
    Saves the uploaded profile picture if a valid file is provided.
    """
    current_user.fname = request.form['fname']
    current_user.lname = request.form['lname']

    new_phone: str = request.form['phone'].strip()
    if new_phone and new_phone != current_user.phone:
        if not validate_phone(new_phone):
            flash(_('Invalid phone number format.'), 'danger')
            return
        current_user.phone = new_phone

    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file.filename and file.filename != '':
            s, extension = os.path.splitext(file.filename)
            if extension and extension.lower() in current_app.config['IMG_FORMATS']:
                filename: str = secure_filename(file.filename)
                if not filename:
                    filename = f'{current_user.id}_profile_pic.png'

                os.makedirs(current_app.config['PROFILE_PICS_FOLDER'], exist_ok=True)
                file.save(os.path.join(current_app.config['PROFILE_PICS_FOLDER'], filename))
                current_user.profile_picture = filename
            else:
                flash(_('Invalid file type. Only PNG, JPG, and BMP files are allowed.'), 'danger')

    db.session.commit()
    flash(_('Profile updated successfully.'), 'success')


def handle_change_language() -> None:
    """
    Handle changing the user's preferred language setting.
    """
    language: str = request.form['language']
    current_user.language = language
    db.session.commit()
    flash(_('Language changed successfully.'), 'success')


def handle_update_notification_settings() -> None:
    """
    Handle updating the user's notification preferences.
    """
    current_user.notifications_enabled = 'notifications_enabled' in request.form
    current_user.email_notifications_enabled = 'email_notifications_enabled' in request.form
    db.session.commit()
    flash(_('Notification settings updated successfully.'), 'success')


def handle_social_login(provider: any, name: str = "facebook") -> Response:
    """
    Handle social login process for various providers.
    Connects the social account to the user's profile if not already connected.

    Args:
        provider: The OAuth2 provider blueprint.
        name: The name of the social media platform (default is "facebook").

    Returns:
        Optional[Response]: A redirect response or None.
    """
    if not provider.authorized:
        return redirect(url_for(f'{name}.login'))

    resp: any = provider.get('/me?fields=id,name,email')
    if not resp.ok:
        flash(f'Failed to fetch user info from {name.capitalize()}', 'error')
        return redirect(url_for('profile.profile_info'))

    account_info: dict[str, any] = resp.json()
    social_id: str = account_info['id']

    existing_social_account: Optional[SocialAccount] = db.session.query(SocialAccount).filter_by(
        provider=name,
        social_id=social_id
    ).first()

    if existing_social_account:
        if existing_social_account.user_id == current_user.id:
            flash(f'This {name.capitalize()} account is already connected to your profile.', 'info')
        else:
            flash(f'This {name.capitalize()} account is already connected to another user.', 'error')
    else:
        new_social_account: SocialAccount = SocialAccount(
            user_id=current_user.id,
            provider=name,
            social_id=social_id,
            access_token=provider.token['access_token']
        )
        db.session.add(new_social_account)
        db.session.commit()
        flash(f'{name.capitalize()} account successfully connected to your profile.', 'success')

    return redirect(url_for('profile.profile_info'))
