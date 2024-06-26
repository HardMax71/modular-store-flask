import os

import phonenumbers
from flask import request, flash, redirect, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_user
from phonenumbers import NumberParseException
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from config import AppConfig
from modules.db.database import db_session
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
        existing_user = db_session.query(User).filter_by(email=new_email).first()
        if not existing_user:
            current_user.email = new_email
            db_session.commit()
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
            db_session.commit()
            flash(_('Password changed successfully.'), 'success')
        else:
            flash(_('The new password and confirmation do not match.'), 'danger')
    else:
        flash(_('Incorrect current password.'), 'danger')


def handle_change_phone():
    new_phone = request.form['phone'].strip()
    if new_phone and new_phone != current_user.phone:
        try:
            phone_number = phonenumbers.parse(new_phone, None)
            if not phonenumbers.is_valid_number(phone_number):
                raise NumberParseException(0, "Invalid phone number")

            current_user.phone = new_phone
            db_session.commit()
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
    db_session.commit()
    flash(_('Profile updated successfully.'), 'success')


def handle_change_language():
    language = request.form['language']
    current_user.language = language
    db_session.commit()
    flash(_('Language changed successfully.'), 'success')


def handle_update_notification_settings():
    current_user.notifications_enabled = 'notifications_enabled' in request.form
    current_user.email_notifications_enabled = 'email_notifications_enabled' in request.form
    db_session.commit()
    flash(_('Notification settings updated successfully.'), 'success')


def handle_social_login(provider):
    if not provider.authorized:
        return redirect(url_for(f'{provider.name}.login'))

    account_info = provider.get('/me?fields=id,name,email').json()
    social_id = account_info['id']
    username = account_info['name']
    email = account_info['email']

    social_account = db_session.query(SocialAccount).filter_by(provider=provider.name, social_id=social_id).first()

    if social_account:
        login_user(social_account.user)
    else:
        new_random_password = os.urandom(16).hex()
        user = User(username=username,
                    email=email,
                    password=str(generate_password_hash(new_random_password)))
        db_session.add(user)
        db_session.commit()

        social_account = SocialAccount(user_id=user.id, provider=provider.name, social_id=social_id)
        db_session.add(social_account)
        db_session.commit()

        login_user(user)

    return redirect(url_for('profile.profile_info'))
