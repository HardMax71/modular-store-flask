from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_babel import gettext as _
from flask_dance.contrib.facebook import facebook
from flask_dance.contrib.google import google
from flask_login import current_user, login_required

from config import AppConfig
from modules.db.database import db_session
from modules.db.models import Address, Notification
from modules.decorators import login_required_with_message
from .utils import (
    handle_profile_update, handle_social_login
)

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/', methods=['GET', 'POST'])
@login_required_with_message(message=_("You must be logged in to open profile."))
def profile_info():
    if request.method == 'POST':
        handle_profile_update()

    return render_template('profile.html',
                           user=current_user,
                           languages=AppConfig.LANGUAGES,
                           lang_names=AppConfig.LANGUAGE_NAMES)


@profile_bp.route('/notifications')
@login_required
def notifications():
    user_notifications = db_session.query(Notification).filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()).all()
    return render_template('notifications.html',
                           notifications=user_notifications)


@profile_bp.route('/notifications/<int:notification_id>/mark-as-read', methods=['POST'])
@login_required
def mark_notification_as_read(notification_id):
    notification = db_session.query(Notification).get(notification_id)
    if not notification:
        flash(_('Notification not found.'), 'danger')
        return redirect(url_for('profile.notifications'))
    if notification.user_id != current_user.id:
        flash(_('You do not have permission to mark this notification as read.'), 'danger')
        return redirect(url_for('profile.profile_info'))
    notification.read = True
    db_session.commit()
    return redirect(url_for('profile.notifications'))


@profile_bp.route('/add-address', methods=['GET', 'POST'])
@login_required_with_message(message=_("You must be logged in to add an address."))
def add_address():
    if request.method == 'POST':
        address_data = {
            'address_line1': request.form.get('address_line1'),
            'address_line2': request.form.get('address_line2'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'zip_code': request.form.get('zip_code'),
            'country': request.form.get('country')
        }

        existing_address = db_session.query(Address).filter_by(user_id=current_user.id, **address_data).first()

        if existing_address:
            flash(_('This address has already been added.'), 'warning')
            return redirect(url_for('profile.profile_info'))

        new_address = Address(user_id=current_user.id, **address_data)
        db_session.add(new_address)
        db_session.commit()
        flash(_('Address added successfully.'), 'success')

        return redirect(url_for('profile.profile_info'))

    return render_template('add_address.html')


@profile_bp.route('/addresses/edit/<int:address_id>', methods=['GET', 'POST'])
@login_required
def edit_address(address_id):
    address = db_session.query(Address).get(address_id)
    if not address:
        flash(_('Address not found.'), 'danger')
        return redirect(url_for('profile.profile_info'))
    if address.user_id != current_user.id:
        flash(_('You do not have permission to edit this address.'), 'danger')
        return redirect(url_for('profile.profile_info'))
    if request.method == 'POST':
        address.address_line1 = request.form['address_line1']
        address.address_line2 = request.form['address_line2']
        address.city = request.form['city']
        address.state = request.form['state']
        address.zip_code = request.form['zip_code']
        address.country = request.form['country']
        db_session.commit()
        flash(_('Address updated successfully.'), 'success')
        return redirect(url_for('profile.profile_info'))
    return render_template('edit_address.html', address=address)


@profile_bp.route('/addresses/delete/<int:address_id>', methods=['POST'])
@login_required
def delete_address(address_id):
    address = db_session.query(Address).get(address_id)
    if not address:
        flash(_('Address not found.'), 'danger')
        return redirect(url_for('profile.profile_info'))
    if address.user_id != current_user.id:
        flash(_('You do not have permission to delete this address.'), 'danger')
    else:
        db_session.delete(address)
        db_session.commit()
        flash(_('Address deleted successfully.'), 'success')
    return redirect(url_for('profile.profile_info'))


@profile_bp.route('/facebook-login')
def facebook_login():
    return handle_social_login(facebook)


@profile_bp.route('/google-login')
def google_login():
    return handle_social_login(google)


def init_profile(app):
    app.register_blueprint(profile_bp, url_prefix='/profile')
