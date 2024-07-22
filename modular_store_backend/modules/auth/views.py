from typing import Optional

from flask import Blueprint, redirect, render_template, request, flash, url_for, current_app
from flask import Flask
from flask.typing import ResponseValue
from flask_babel import gettext as _
from flask_limiter import Limiter
from flask_login import login_user, logout_user
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer as Serializer
from itsdangerous.exc import BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash

from modular_store_backend.forms.forms import RegistrationForm, LoginForm
from modular_store_backend.modules.db.database import db
from modular_store_backend.modules.db.models import User, SocialAccount
from modular_store_backend.modules.decorators import login_required_with_message
from modular_store_backend.modules.oauth_login import oauth

auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/register", methods=['GET', 'POST'])
def register() -> ResponseValue:
    form = RegistrationForm()
    if form.validate_on_submit():
        if db.session.query(User).filter_by(username=form.username.data).first():  # such user already exists
            flash(_("Username already exists. Please choose a different one."), "danger")
        elif not form.password.data:
            flash(_("Password cannot be empty."), "danger")
        else:
            hashed_password: str = generate_password_hash(form.password.data)
            new_user: User = User(username=form.username.data,
                                  password=hashed_password,
                                  email=form.email.data)
            db.session.add(new_user)
            db.session.commit()
            db.session.flush()
            flash(_("Registration successful. Please log in."), "success")
            return redirect(url_for('auth.login'))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in the {getattr(form, field).label.text} field - {error}", "danger")
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=['GET', 'POST'])
def login() -> ResponseValue:
    form = LoginForm()
    if form.validate_on_submit():
        user: Optional[User] = db.session.query(User).filter_by(username=form.username.data).first()
        if user and form.password.data and check_password_hash(user.password, form.password.data):
            db.session.refresh(user)
            login_user(user)
            flash(_("Login successful."), "success")
            return redirect(url_for('main.index'))
        else:
            flash(_("Invalid username or password."), "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required_with_message(message=_("You must be logged in to log out."), category="danger")
def logout() -> ResponseValue:
    logout_user()
    flash(_("You have been logged out."), "success")
    return redirect(url_for('main.index'))


@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password() -> ResponseValue:
    if request.method == 'POST':
        email: Optional[str] = request.form['email']
        user: Optional[User] = (
            db.session.query(User)
            .filter_by(email=email)
            .first()
        )
        if user:
            if not email:
                flash(_('Please enter your email address first.'), 'warning')
                return redirect(url_for('auth.reset_password'))

            # Generate password reset token
            s = Serializer(current_app.config['SECRET_KEY'],
                           str(current_app.config['PASSWORD_RESET_TIMEOUT']))
            token = s.dumps({'user_id': user.id})

            # Send password reset email
            msg = Message('Password Reset Request',
                          sender=current_app.config['MAIL_DEFAULT_SENDER'],
                          recipients=[user.email])
            reset_url = url_for('auth.reset_password_token', token=token, _external=True)
            msg.body = f'''To reset your password, visit the following link:
                {reset_url}

                If you did not make this request, simply ignore this email and no changes will be made.
                '''

            # should work, turn off for now
            # mail.send(msg)
            # flash('Password reset email sent. Please check your inbox.', 'success')
            flash(_('Sending email is disabled for now.'), 'warning')
        else:
            flash(_('No account found with that email.'), 'warning')
    return render_template('auth/reset_password.html')


@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password_token(token: str) -> ResponseValue:
    s = Serializer(current_app.config['SECRET_KEY'])
    try:
        data = s.loads(token)
    except SignatureExpired:
        flash(_('The password reset token has expired.'), 'danger')
        return redirect(url_for('auth.reset_password'))
    except BadSignature:
        flash(_('Invalid token.'), 'danger')
        return redirect(url_for('auth.reset_password'))

    user: Optional[User] = db.session.get(User, data['user_id'])
    if not user:
        flash(_('Invalid user.'), 'danger')
        return redirect(url_for('auth.reset_password'))

    if request.method == 'POST':
        new_password: Optional[str] = request.form['new_password']
        confirm_password: Optional[str] = request.form['confirm_password']
        if not new_password or not confirm_password:
            flash(_('Please enter a new password.'), 'warning')
            return redirect(url_for('auth.reset_password_token', token=token))

        if new_password == confirm_password:
            user.password = generate_password_hash(new_password)
            db.session.commit()
            flash(_('Your password has been reset. You can now log in with the new password.'), 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(_('Passwords do not match.'), 'danger')

    return render_template('auth/reset_password_token.html')


@auth_bp.route('/login/google')
def google_login():
    google = oauth.create_client('google')
    redirect_uri = url_for('auth.google_authorize', _external=True)
    return google.authorize_redirect(redirect_uri)


@auth_bp.route('/login/google/authorize')
def google_authorize():
    google = oauth.create_client('google')
    token = google.authorize_access_token()
    resp = google.get('https://www.googleapis.com/oauth2/v3/userinfo')
    user_info = resp.json()

    # Check if user already exists by social_id
    social_account = db.session.query(SocialAccount).filter_by(provider='google', social_id=user_info['sub']).first()

    if social_account:
        user = social_account.user
    else:
        # Check if a user with this email already exists
        user = db.session.query(User).filter_by(email=user_info['email']).first()

        if not user:
            # Create new user
            password = str(Serializer(current_app.config['SECRET_KEY']).dumps({'google_id': user_info['sub']}))[:8]
            user = User(
                username=user_info['email'],
                email=user_info['email'],
                fname=user_info.get('given_name'),
                lname=user_info.get('family_name'),
                password=generate_password_hash(password),
                _profile_picture=user_info.get('picture', 'user-icon.png')
            )
            db.session.add(user)
            db.session.flush()

            flash(_(f"Your account has been created.\nPassword: {password}"), "warning")

        # Create social account
        social_account = SocialAccount(
            user_id=user.id,
            provider='google',
            social_id=user_info['sub'],
            access_token=token['access_token']
        )
        db.session.add(social_account)

    db.session.commit()
    login_user(user)
    flash(_("Login with Google successful."), "success")
    return redirect(url_for('main.index'))


def init_auth(app: Flask, limiter: Limiter) -> None:
    app.register_blueprint(auth_bp)
    limiter.limit(app.config['DEFAULT_LIMIT_RATE'])(auth_bp)
