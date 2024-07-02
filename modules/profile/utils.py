import os

import phonenumbers
from flask import request, flash, redirect, url_for
from flask_babel import gettext as _
from flask_login import current_user
from phonenumbers import NumberParseException
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from config import AppConfig
from modules.db.database import db
from modules.db.models import User, SocialAccount


def handle_profile_update():
    form_actions = {
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


def handle_change_email():
    new_email = request.form['email'].strip()
    if new_email and new_email != current_user.email:
        existing_user = User.query.filter(User.email == new_email, User.id != current_user.id).first()
        if not existing_user:
            current_user.email = new_email
            db.session.commit()
            flash(_('Email changed successfully.'), 'success')
        else:
            flash(_('This email is already in use.'), 'warning')
    else:
        flash(_('New email is either empty or same as previous one.'), 'warning')


def handle_change_password():
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']
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


def handle_change_phone():
    new_phone = request.form['phone'].strip()
    if new_phone and new_phone != current_user.phone:
        try:
            phone_number = phonenumbers.parse(new_phone, None)
            if not phonenumbers.is_valid_number(phone_number):
                raise NumberParseException(0, "Invalid phone number")

            current_user.phone = new_phone
            db.session.commit()
            flash(_('Phone number successfully changed.'), 'success')
        except NumberParseException:
            flash(_('Invalid phone number format.'), 'danger')
    else:
        flash(_('The new phone number matches the current one or is empty.'), 'warning')


def handle_update_profile():
    current_user.fname = request.form['fname']
    current_user.lname = request.form['lname']
    current_user.phone = request.form['phone']
    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file.filename != '':
            s, extension = os.path.splitext(file.filename)
            extension = extension.lower()
            if extension in AppConfig.IMG_FORMATS:
                filename = secure_filename(file.filename)
                os.makedirs(AppConfig.PROFILE_PICS_FOLDER, exist_ok=True)
                file.save(os.path.join(AppConfig.PROFILE_PICS_FOLDER, filename))
                current_user.profile_picture = filename
            else:
                flash(_('Invalid file type. Only PNG, JPG, and BMP files are allowed.'), 'danger')
    db.session.commit()
    flash(_('Profile updated successfully.'), 'success')


def handle_change_language():
    language = request.form['language']
    current_user.language = language
    db.session.commit()
    flash(_('Language changed successfully.'), 'success')


def handle_update_notification_settings():
    current_user.notifications_enabled = 'notifications_enabled' in request.form
    current_user.email_notifications_enabled = 'email_notifications_enabled' in request.form
    db.session.commit()
    flash(_('Notification settings updated successfully.'), 'success')


def handle_social_login(provider, name: str = None):
    if not provider.authorized:
        return redirect(url_for(f'{name}.login'))

    resp = provider.get('/me?fields=id,name,email')
    if not resp.ok:
        flash(f'Failed to fetch user info from {name.capitalize()}', 'error')
        return redirect(url_for('profile.profile_info'))

    account_info = resp.json()
    social_id = account_info['id']

    # Check if this social account is already connected to any user
    existing_social_account = db.session.query(SocialAccount).filter_by(
        provider=name,
        social_id=social_id
    ).first()

    if existing_social_account:
        if existing_social_account.user_id == current_user.id:
            flash(f'This {name.capitalize()} account is already connected to your profile.', 'info')
        else:
            flash(f'This {name.capitalize()} account is already connected to another user.', 'error')
    else:
        # Connect the social account to the current user
        new_social_account = SocialAccount(
            user_id=current_user.id,
            provider=name,
            social_id=social_id,
            access_token=provider.token['access_token']
        )
        db.session.add(new_social_account)
        db.session.commit()
        flash(f'{name.capitalize()} account successfully connected to your profile.', 'success')

    return redirect(url_for('profile.profile_info'))
