from flask_babel import gettext as _
from flask_wtf import FlaskForm
from wtforms import PasswordField
from wtforms import StringField, TextAreaField, SubmitField, FileField
from wtforms.validators import DataRequired
from wtforms.validators import Email, EqualTo, Length


class RegistrationForm(FlaskForm):  # type: ignore
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField(_('Sign Up'))


class LoginForm(FlaskForm):  # type: ignore
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    submit = SubmitField(_('Login'))


class EmailForm(FlaskForm):  # type: ignore
    subject = StringField(_('Subject'), validators=[DataRequired()])
    body = TextAreaField(_('Body'), validators=[DataRequired()])
    attachments = FileField(_('Attachments'))
    submit = SubmitField(_('Send Email'))
