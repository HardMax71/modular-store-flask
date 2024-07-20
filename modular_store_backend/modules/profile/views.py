from flask import Blueprint, render_template, request, flash, redirect, url_for, Flask, current_app
from flask.typing import ResponseValue
from flask_babel import gettext as _
from flask_dance.contrib.facebook import facebook
from flask_dance.contrib.google import google
from flask_login import current_user, login_required

from modular_store_backend.modules.db.database import db
from modular_store_backend.modules.db.models import Address, Notification
from modular_store_backend.modules.decorators import login_required_with_message
from modular_store_backend.modules.profile.utils import handle_profile_update, handle_social_login

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/', methods=['GET', 'POST'])
@login_required_with_message(message=_("You must be logged in to open profile."))
def profile_info() -> ResponseValue:
    """Render the profile page and handle profile updates."""
    if request.method == 'POST':
        handle_profile_update()

    return render_template('profile.html',
                           user=current_user,
                           languages=current_app.config['LANGUAGES'],
                           lang_names=current_app.config['LANGUAGE_NAMES'])


@profile_bp.route('/notifications')
@login_required  # type: ignore
def notifications() -> ResponseValue:
    """Render the notifications page for the current user."""
    user_notifications = db.session.query(Notification).filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()).all()
    return render_template('notifications.html',
                           notifications=user_notifications)


@profile_bp.route('/notifications/<int:notification_id>/mark-as-read', methods=['POST'])
@login_required  # type: ignore
def mark_notification_as_read(notification_id: int) -> ResponseValue:
    """Mark a notification as read."""
    notification = db.session.get(Notification, notification_id)
    if not notification:
        flash(_('Notification not found.'), 'danger')
        return redirect(url_for('profile.notifications'))
    if notification.user_id != current_user.id:
        flash(_('You do not have permission to mark this notification as read.'), 'danger')
        return redirect(url_for('profile.profile_info'))
    notification.read = True
    db.session.commit()
    return redirect(url_for('profile.notifications'))


@profile_bp.route('/add-address', methods=['GET', 'POST'])
@login_required_with_message(message=_("You must be logged in to add an address."))
def add_address() -> ResponseValue:
    """Add a new address for the current user."""
    if request.method == 'POST':
        address_data = {
            'user_id': current_user.id,
            'address_line1': request.form.get('address_line1'),
            'address_line2': request.form.get('address_line2'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'zip_code': request.form.get('zip_code'),
            'country': request.form.get('country')
        }

        existing_address = db.session.query(Address).filter_by(**address_data).first()

        if existing_address:
            flash(_('This address has already been added.'), 'warning')
            return redirect(url_for('profile.profile_info'))

        new_address = Address(**address_data)
        db.session.add(new_address)
        db.session.commit()
        flash(_('Address added successfully.'), 'success')

        return redirect(url_for('profile.profile_info'))

    return render_template('add_address.html')


@profile_bp.route('/addresses/edit/<int:address_id>', methods=['GET', 'POST'])
@login_required  # type: ignore
def edit_address(address_id: int) -> ResponseValue:
    """Edit an existing address for the current user."""
    address = db.session.get(Address, address_id)
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
        db.session.commit()
        flash(_('Address updated successfully.'), 'success')
        return redirect(url_for('profile.profile_info'))
    return render_template('edit_address.html', address=address)


@profile_bp.route('/addresses/delete/<int:address_id>', methods=['POST'])
@login_required  # type: ignore
def delete_address(address_id: int) -> ResponseValue:
    """Delete an existing address for the current user."""
    address = db.session.get(Address, address_id)
    if not address:
        flash(_('Address not found.'), 'danger')
        return redirect(url_for('profile.profile_info'))
    if address.user_id != current_user.id:
        flash(_('You do not have permission to delete this address.'), 'danger')
    else:
        db.session.delete(address)
        db.session.commit()
        flash(_('Address deleted successfully.'), 'success')
    return redirect(url_for('profile.profile_info'))


@profile_bp.route('/facebook-login')
def facebook_login() -> ResponseValue:
    """Handle login via Facebook."""
    return handle_social_login(facebook, name='facebook')


@profile_bp.route('/google-login')
def google_login() -> ResponseValue:
    """Handle login via Google."""
    return handle_social_login(google, name='google')


def init_profile(app: Flask) -> None:
    """Initialize the profile blueprint."""
    app.register_blueprint(profile_bp, url_prefix='/profile')
