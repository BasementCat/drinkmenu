from wtforms import StringField, TextAreaField, BooleanField, FileField, SubmitField, SelectField
from wtforms.validators import DataRequired

from . import BaseForm, HasImageMixin
from app.database import DrinkComponent


class DrinkForm(HasImageMixin(), BaseForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    is_orderable = BooleanField('Is Orderable')
    has_strengths = BooleanField('Has Strengths')
    in_stock = BooleanField('In Stock')
    image = FileField('Image')

    submit = SubmitField('Save')


class DrinkComponentForm(HasImageMixin(), BaseForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    type_ = SelectField('Type', choices=list(DrinkComponent.TYPES.items()), validators=[DataRequired()])
    in_stock = BooleanField('In Stock')
    image = FileField('Image')

    submit = SubmitField('Save')
