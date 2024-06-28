from flask import Blueprint, redirect, render_template, request, flash, url_for
from flask_babel import gettext as _
from flask_login import login_user, logout_user
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer as Serializer
from itsdangerous.exc import BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash

from config import AppConfig
from forms.forms import RegistrationForm, LoginForm
from modules.db.database import db
from modules.db.models import User
from modules.decorators import login_required_with_message

auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = (db.session.query(User.id)
                         .filter_by(username=form.username.data).first())
        if existing_user:
            flash(_("Username already exists. Please choose a different one."), "danger")
        else:
            hashed_password = generate_password_hash(form.password.data)
            new_user = User(username=form.username.data,
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
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.query(User).filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            db.session.refresh(user)
            login_user(user)
            flash(_("Login successful."), "success")
            return redirect(url_for('main.index'))
        else:
            flash(_("Invalid username or password."), "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required_with_message(message=_("You must be logged in to log out."), category="danger")
def logout():
    logout_user()
    flash(_("You have been logged out."), "success")
    return redirect(url_for('main.index'))


@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            # Generate password reset token
            s = Serializer(AppConfig.SECRET_KEY, str(1800))  # Token valid for 30 minutes
            token = s.dumps({'user_id': user.id})

            # Send password reset email
            msg = Message('Password Reset Request',
                          sender=AppConfig.MAIL_DEFAULT_SENDER,
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
def reset_password_token(token):
    s = Serializer(AppConfig.SECRET_KEY)
    try:
        data = s.loads(token)
    except SignatureExpired:
        flash(_('The password reset token has expired.'), 'danger')
        return redirect(url_for('auth.reset_password'))
    except BadSignature:
        flash(_('Invalid token.'), 'danger')
        return redirect(url_for('auth.reset_password'))

    user = User.query.get(data['user_id'])
    if not user:
        flash(_('Invalid user.'), 'danger')
        return redirect(url_for('auth.reset_password'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        if new_password == confirm_password:
            user.password = generate_password_hash(new_password)
            db.session.commit()
            flash(_('Your password has been reset. You can now log in with the new password.'), 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(_('Passwords do not match.'), 'danger')

    return render_template('auth/reset_password_token.html')


def init_auth(app, limiter):
    app.register_blueprint(auth_bp)
    limiter.limit(AppConfig.DEFAULT_LIMIT_RATE)(auth_bp)
