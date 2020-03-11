from wtforms import StringField, SubmitField
from wtforms.validators import Optional

from . import BaseForm
from app.database import RuntimeConfig


def ConfigForm(*args, drink=None, **kwargs):
    class ConfigFormImpl(BaseForm):
        pass

    for k in RuntimeConfig.get_fields():
        setattr(ConfigFormImpl, k, StringField(k, validators=[Optional()]))

    ConfigFormImpl.submit = SubmitField('Save')

    return ConfigFormImpl(*args, **kwargs)
