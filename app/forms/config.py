from wtforms import StringField, SubmitField, BooleanField
from wtforms.validators import Optional

from . import BaseForm
from app.database import RuntimeConfig, Event


def ConfigForm(*args, drink=None, **kwargs):
    class ConfigFormImpl(BaseForm):
        pass

    for k in RuntimeConfig.get_fields():
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

    ConfigFormImpl.submit = SubmitField('Save')

    return ConfigFormImpl(*args, **kwargs)
