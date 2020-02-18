import os
import uuid

from flask import g, current_app

from tinydb import TinyDB, Query

from marshmallow import Schema, fields

def db():
    if 'db' not in g:
        g.db = TinyDB(os.path.join(current_app.config['DATA_DIRECTORY'], 'db.json'))
    return g.db


class BaseSchema(Schema):
    pass


class Model:
    def __init__(self, *args, **kwargs):
        self._load_self(kwargs)

    @classmethod
    def _get_table_name(cls):
        return cls.__name__

    @classmethod
    def _get_table(cls):
        return db().table(cls._get_table_name())

    @classmethod
    def _get_schema(cls):
        if not hasattr(cls, '_schema_instance'):
            cls._schema_instance = cls._schema()
        return cls._schema_instance

    def _load_self(self, data):
        res = self._get_schema().load(data)
        self.doc_id = getattr(data, 'doc_id', None)
        for k, v in res.items():
            setattr(self, k, v)

    @classmethod
    def all(cls):
        return cls._get_table().all()

    @classmethod
    def get(cls, doc_id):
        res = cls._get_table().get(doc_id=doc_id)
        if not res:
            return None
        out = cls()
        out._load_self(res)
        return out

    def save(self):
        data = self._get_schema().dump(self)
        if self.doc_id:
            self._get_table().update(data, doc_ids=[self.doc_id])
        else:
            self.doc_id = self._get_table().insert(data)

    def delete(self):
        if self.doc_id:
            self._get_table().remove(doc_ids=[self.doc_id])
            self.doc_id = None


def HasImageMixin(image_field_name='image'):
    class HasImageMixinImpl:
        def delete(self):
            super().delete()
            imgname = getattr(self, image_field_name)
            if imgname:
                filename = os.path.join(current_app.config['DATA_DIRECTORY'], 'images', imgname)
                if os.path.exists(filename):
                    os.unlink(filename)
    return HasImageMixinImpl


class Drink(HasImageMixin(), Model):
    class _schema(BaseSchema):
        name = fields.Str()
        description = fields.Str()
        is_orderable = fields.Boolean(default=True)
        has_strengths = fields.Boolean(default=True)
        has_mocktail = fields.Boolean(default=False)
        in_stock = fields.Boolean(default=True)
        image = fields.Str()


class DrinkComponent(HasImageMixin(), Model):
    TYPES = {
        'liquor': 'Liquor',
        'mixer': 'Mixer',
        'other': 'Other',
    }

    class _schema(BaseSchema):
        name = fields.Str()
        description = fields.Str()
        type_ = fields.Str()
        in_stock = fields.Boolean(default=True)
        image = fields.Str()