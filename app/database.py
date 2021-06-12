import os
import uuid
import threading
import datetime

from flask import g, current_app

from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
from tinydb.middlewares import Middleware

from marshmallow import Schema, fields


class ThreadingMiddleware(Middleware):
    locks = {}

    def __init__(self, name, storage_cls):
        # Initialize the parent constructor
        super().__init__(storage_cls)
        self.name = name
        self.locks.setdefault(self.name, threading.RLock())

    def read(self):
        with self.locks[self.name]:
            return self.storage.read()

    def write(self, data):
        with self.locks[self.name]:
            return self.storage.write(data)


def db():
    if 'db' not in g:
        filename = os.path.join(current_app.config['DATA_DIRECTORY'], 'db.json')
        g.db = TinyDB(filename, storage=ThreadingMiddleware(filename, JSONStorage))
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

    @classmethod
    def _load_raw(cls, data):
        o = cls()
        o._load_self(data)
        return o

    def _load_self(self, data):
        res = self._get_schema().load(data)
        self.doc_id = getattr(data, 'doc_id', None)
        for k, v in res.items():
            setattr(self, k, v)

    @staticmethod
    def _sorted_results(coll, sort_key):
        if sort_key:
            fn = sort_key if callable(sort_key) else lambda doc: getattr(doc, sort_key, 1)
            yield from sorted(coll, key=fn)
        else:
            yield from coll

    @classmethod
    def all(cls, sort_key=None):
        def _fetch():
            for res in cls._get_table().all():
                o = cls()
                o._load_self(res)
                yield o

        yield from cls._sorted_results(_fetch(), sort_key)

    @classmethod
    def get(cls, doc_id):
        res = cls._get_table().get(doc_id=doc_id)
        if not res:
            return None
        out = cls()
        out._load_self(res)
        return out

    @classmethod
    def find(cls, *doc_ids, sort_key=None, **filters):
        def _fetch():
            if doc_ids:
                return list(filter(None, (cls.get(i) for i in doc_ids)))

            query = Query()
            conditions = []
            for k, v in filters.items():
                conditions.append(getattr(query, k) == v)
            search = conditions.pop(0)
            for cond in conditions:
                search = search & cond
            return list(map(cls._load_raw, cls._get_table().search(search)))

        return list(cls._sorted_results(_fetch(), sort_key))

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


class OrderableMixin:
    class _schema:
        order = fields.Integer(default=10000, missing=10000)

    @classmethod
    def set_order(cls, order_by_id):
        for doc in cls.all():
            if doc.doc_id in order_by_id and doc.order != order_by_id[doc.doc_id]:
                doc.order = order_by_id[doc.doc_id]
                doc.save()


# TODO: this probably doesn't belong here
STRENGTHS = {
    'mocktail': 'Mocktail',
    'light': 'Light',
    'normal': 'Normal',
    'strong': 'Strong',
}
DEFAULT_STRENGTH = 'normal'


class Drink(OrderableMixin, HasImageMixin(), Model):
    class _schema(OrderableMixin._schema, BaseSchema):
        name = fields.Str(missing=None)
        description = fields.Str(missing=None)
        is_orderable = fields.Boolean(default=True, missing=True)
        has_strengths = fields.Boolean(default=True, missing=True)
        has_mocktail = fields.Boolean(default=False, missing=False)
        in_stock = fields.Boolean(default=True, missing=True)
        inventory_level = fields.Integer(default=None, missing=None)
        image = fields.Str(missing=None)


class DrinkComponent(OrderableMixin, HasImageMixin(), Model):
    TYPES = {
        'liquor': 'Liquor',
        'mixer': 'Mixer',
        'other': 'Other',
    }

    class _schema(OrderableMixin._schema, BaseSchema):
        name = fields.Str(missing=None)
        description = fields.Str(missing=None)
        type_ = fields.Str(missing=None)
        in_stock = fields.Boolean(default=True, missing=True)
        image = fields.Str(missing=None)


class SavedOrder(Model):
    class _schema(BaseSchema):
        drink_name = fields.Str(missing=None)
        drink_components = fields.List(fields.Integer(), missing=lambda: [])


class Event(Model):
    class _schema(BaseSchema):
        name = fields.Str(missing=None)
        date = fields.DateTime(missing=datetime.datetime.utcnow)
        is_current = fields.Boolean(default=False, missing=False)

    @classmethod
    def get_current(cls):
        res = cls.find(sort_key='date', is_current=True)
        if res:
            return res[-1]

    @classmethod
    def get_current_id(cls):
        res = cls.get_current()
        if res:
            return res.doc_id


class Order(Model):
    class _schema(BaseSchema):
        event = fields.Integer(missing=None)
        name = fields.Str(missing=None)
        drink_name = fields.Str(allow_none=True, missing=None)
        drink = fields.Integer(missing=None)
        drink_components = fields.List(fields.Integer(), missing=lambda: [])
        strength = fields.Str(missing=None)
        printed = fields.Boolean(default=False, missing=False)


class RuntimeConfig(Model):
    class _schema(BaseSchema):
        user_pass = fields.Str(allow_none=True, missing=None)
        admin_pass = fields.Str(allow_none=True, missing=None)
        logo = fields.Str(allow_none=True, missing=None)

    @classmethod
    def get_fields(cls):
        for k, v in cls._schema._declared_fields.items():
            if isinstance(v, fields.Field):
                yield k

    @classmethod
    def get_single(cls):
        res = list(cls.all())
        if res:
            return res[0]
        return cls()


class Device(Model):
    class _schema(BaseSchema):
        device_id = fields.Str(allow_none=False)
        is_house_device = fields.Boolean(allow_none=False, missing=False)
        use_osk = fields.Boolean(allow_none=False, missing=False)

    @classmethod
    def get_by_devid(cls, devid):
        res = cls.find(device_id=devid)
        if res:
            # TODO: more than one w/ same devid is invalid
            return res[0]
        return None


class OrderStat(Model):
    class _schema(BaseSchema):
        event = fields.Integer(missing=None)
        drink = fields.Integer(missing=None)
        drink_components = fields.List(fields.Integer(), missing=lambda: [])
        strength = fields.Str(missing=None)

    @classmethod
    def from_order(cls, order):
        o = cls(event=Event.get_current_id(), drink=order.drink, drink_components=order.drink_components[:], strength=order.strength)
        o.save()
