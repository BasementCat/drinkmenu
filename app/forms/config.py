from flask import url_for

from wtforms import StringField, SubmitField, BooleanField, FileField
from wtforms.validators import Optional

from . import BaseForm, HasImageMixin
from app.database import RuntimeConfig, Event


def ConfigForm(*args, drink=None, **kwargs):
    class ConfigFormImpl(HasImageMixin(image_field_name='logo'), BaseForm):
        pass

    for k in RuntimeConfig.get_fields():
        if k == 'logo':
            continue
        setattr(ConfigFormImpl, k, StringField(k, validators=[Optional()]))

    current_event = Event.get_current()
    ev_desc = 'Entering a value here will begin a new event, any orders created or stats collected will belong to that event.'
    if current_event:
        ev_desc += f'  The current event is "{current_event.name}".'
    ConfigFormImpl.new_event = StringField(
        'Begin New Event',
        validators=[Optional()],
        description=ev_desc
    )

    logo_desc = "Logo to print on receipts."
    logo = RuntimeConfig.get_single().logo
    if logo:
        logo = url_for('index.images', name=logo, mode='full')
        logo_desc += f'Current logo:<br /><img src="{logo}" />'
    ConfigFormImpl.logo = FileField('Logo', description=logo_desc)

    ConfigFormImpl.submit = SubmitField('Save')

    return ConfigFormImpl(*args, **kwargs)
