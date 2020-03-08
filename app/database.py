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
        for res in cls._get_table().all():
            o = cls()
            o._load_self(res)
            yield o

    @classmethod
    def get(cls, doc_id):
        res = cls._get_table().get(doc_id=doc_id)
        if not res:
            return None
        out = cls()
        out._load_self(res)
        return out

    @classmethod
    def find(cls, *doc_ids, **filters):
        if doc_ids:
            return list(filter(None, (cls.get(i) for i in doc_ids)))

        query = Query()
        conditions = []
        for k, v in filters.items():
            conditions.append(getattr(query, k) == v)
        search = conditions.pop(0)
        for cond in conditions:
            search = search & cond
        return cls._get_table().search(search)

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


# TODO: this probably doesn't belong here
STRENGTHS = {
    'mocktail': 'Mocktail',
    'light': 'Light',
    'normal': 'Normal',
    'strong': 'Strong',
}
DEFAULT_STRENGTH = 'normal'


class Drink(HasImageMixin(), Model):
    class _schema(BaseSchema):
        name = fields.Str(missing=None)
        description = fields.Str(missing=None)
        is_orderable = fields.Boolean(default=True, missing=True)
        has_strengths = fields.Boolean(default=True, missing=True)
        has_mocktail = fields.Boolean(default=False, missing=False)
        in_stock = fields.Boolean(default=True, missing=True)
        image = fields.Str(missing=None)


class DrinkComponent(HasImageMixin(), Model):
    TYPES = {
        'liquor': 'Liquor',
        'mixer': 'Mixer',
        'other': 'Other',
    }

    class _schema(BaseSchema):
        name = fields.Str(missing=None)
        description = fields.Str(missing=None)
        type_ = fields.Str(missing=None)
        in_stock = fields.Boolean(default=True, missing=True)
        image = fields.Str(missing=None)


class SavedOrder(Model):
    class _schema(BaseSchema):
        drink_name = fields.Str(missing=None)
        drink_components = fields.List(fields.Integer(), missing=lambda: [])


class Order(Model):
    class _schema(BaseSchema):
        name = fields.Str(missing=None)
        drink_name = fields.Str(allow_none=True, missing=None)
        drink = fields.Integer(missing=None)
        drink_components = fields.List(fields.Integer(), missing=lambda: [])
        strength = fields.Str(missing=None)
        printed = fields.Boolean(default=False, missing=False)
