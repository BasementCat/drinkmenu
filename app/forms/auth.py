from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired

from . import BaseForm


class AuthForm(BaseForm):
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField('Log In')
