from flask import Blueprint, render_template, request, flash, redirect, url_for, Flask, current_app
from flask.typing import ResponseValue
from flask_babel import gettext as _
from flask_login import current_user, login_required

from modular_store_backend.modules.db.database import db
from modular_store_backend.modules.db.models import Address, Notification, SocialAccount
from modular_store_backend.modules.decorators import login_required_with_message
from modular_store_backend.modules.oauth_login import oauth
from modular_store_backend.modules.profile.utils import handle_profile_update

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


@profile_bp.route('/connect/google')
@login_required
def connect_google():
    google = oauth.create_client('google')
    redirect_uri = url_for('profile.google_authorize', _external=True)
    return google.authorize_redirect(redirect_uri)


@profile_bp.route('/connect/google/authorize')
@login_required
def google_authorize():
    google = oauth.create_client('google')
    token = google.authorize_access_token()
    resp = google.get('https://www.googleapis.com/oauth2/v3/userinfo')
    user_info = resp.json()

    existing_account = db.session.query(SocialAccount).filter_by(provider='google', social_id=user_info['sub']).first()
    if existing_account:
        if existing_account.user_id == current_user.id:
            flash(_('This Google account is already connected to your profile.'), 'info')
        else:
            flash(_('This Google account is already connected to another user.'), 'danger')
    else:
        new_social_account = SocialAccount(
            user_id=current_user.id,
            provider='google',
            social_id=user_info['sub'],
            access_token=token['access_token']
        )
        db.session.add(new_social_account)
        db.session.commit()
        flash(_('Google account successfully connected.'), 'success')

    return redirect(url_for('profile.profile_info'))


@profile_bp.route('/connect/facebook')
@login_required
def connect_facebook():
    facebook = oauth.create_client('facebook')
    redirect_uri = url_for('profile.authorize_facebook', _external=True)
    return facebook.authorize_redirect(redirect_uri)


@profile_bp.route('/connect/facebook/callback')
@login_required
def authorize_facebook():
    facebook = oauth.create_client('facebook')
    token = facebook.authorize_access_token()
    resp = facebook.get('me?fields=id,name,email')
    user_info = resp.json()

    existing_account = db.session.query(SocialAccount).filter_by(provider='facebook', social_id=user_info['id']).first()
    if existing_account:
        if existing_account.user_id == current_user.id:
            flash(_('This Facebook account is already connected to your profile.'), 'info')
        else:
            flash(_('This Facebook account is already connected to another user.'), 'danger')
    else:
        new_social_account = SocialAccount(
            user_id=current_user.id,
            provider='facebook',
            social_id=user_info['id'],
            access_token=token['access_token']
        )
        db.session.add(new_social_account)
        db.session.commit()
        flash(_('Facebook account successfully connected.'), 'success')

    return redirect(url_for('profile.profile_info'))


@profile_bp.route('/disconnect/<provider>', methods=['POST'])
@login_required
def disconnect_social(provider):
    social_account = db.session.query(SocialAccount).filter_by(user_id=current_user.id, provider=provider).first()
    if social_account:
        db.session.delete(social_account)
        db.session.commit()
        flash(_('Social account disconnected successfully.'), 'success')
    else:
        flash(_('No such social account connected.'), 'danger')
    return redirect(url_for('profile.profile_info'))


def init_profile(app: Flask) -> None:
    app.register_blueprint(profile_bp, url_prefix='/profile')
