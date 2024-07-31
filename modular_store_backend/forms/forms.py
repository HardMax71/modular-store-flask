# /modular_store_backend/forms/forms.py
from flask_babel import gettext as _
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, TextAreaField, SubmitField, FileField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class RegistrationForm(FlaskForm):
    username = StringField(_('Username'), validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField(_('Email'), validators=[DataRequired(), Email()])
    password = PasswordField(_('Password'), validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(_('Confirm Password'), validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField(_('Sign Up'))


class LoginForm(FlaskForm):
    username = StringField(_('Username'), validators=[DataRequired(), Length(min=2, max=50)])
    password = PasswordField(_('Password'), validators=[DataRequired(), Length(min=8)])
    submit = SubmitField(_('Login'))


class EmailForm(FlaskForm):
    subject = StringField(_('Subject'), validators=[DataRequired()])
    body = TextAreaField(_('Body'), validators=[DataRequired()])
    attachments = FileField(_('Attachments'))
    submit = SubmitField(_('Send Email'))
