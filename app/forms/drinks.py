from wtforms import StringField, TextAreaField, BooleanField, FileField, SubmitField
from wtforms.validators import DataRequired

from . import BaseForm, HasImageMixin


class DrinkForm(HasImageMixin(), BaseForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    is_orderable = BooleanField('Is Orderable')
    has_strengths = BooleanField('Has Strengths')
    in_stock = BooleanField('In Stock')
    image = FileField('Image')

    submit = SubmitField('Save')
