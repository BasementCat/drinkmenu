from wtforms import StringField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, ValidationError

from . import BaseForm
from app.database import STRENGTHS


def OrderForm(*args, drink=None, **kwargs):
    class OrderFormImpl(BaseForm):
        name = StringField('Your Name', validators=[DataRequired()])
        if not drink:
            drink_name = StringField('Name Your Drink')
        if not drink or drink.has_strengths:
            _strengths = dict(STRENGTHS)
            if not drink or not drink.has_mocktail:
                del _strengths['mocktail']
            strength = SelectField('Strength', choices=list(_strengths.items()), validators=[DataRequired()])
        if not (drink or kwargs.get('drink_name')):
            save_for_later = BooleanField('Save this drink')

        submit = SubmitField('Order')

        def validate_drink_name(form, field):
            if hasattr(form, 'save_for_later') and form.save_for_later.data and not field.data:
                raise ValidationError("A drink name is required to save for later")

    return OrderFormImpl(*args, **kwargs)
