# -*- coding: utf-8 -*-

from flask import current_app
from flask_sqlalchemy import get_state
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import class_mapper
from sqlalchemy.orm.exc import NoResultFound
from marshmallow_sqlalchemy import ModelSchema
from .manager import RelationalManager
from .exceptions import ItemNotFound, DuplicateKey, BackendConflict
from .utils import get_value

class CustomModelSchema(ModelSchema):

    def make_instance(self, data):
        "Don't return a model, only return dict with data"
        return data

class SQLAlchemyManager(RelationalManager):

    def _init_model(self, resource, model, meta):
        mapper = class_mapper(model)

        self.model = model
        self.id_column = mapper.primary_key[0]
        self.id_attribute = mapper.primary_key[0].name

        self.default_sort_expression = self.id_column.asc()

        if not hasattr(resource.Meta, 'name'):
            meta['name'] = model.__tablename__.lower()

    def _init_schema(self, resource, model, meta):
        Base = CustomModelSchema
        ns = {"Meta": type('Meta', (object,), {"model": model})}
        self.schema_class = type(meta['name']+'Schema', (Base,), ns)

    @property
    def schema(self):
        return self.schema_class(session=self._get_session())

    def get_schema(self, strict=False):
        return self.schema_class(session=self._get_session(), strict=strict)

    @staticmethod
    def _get_session():
        return get_state(current_app).db.session

    @staticmethod
    def _is_change(a, b):
        return (a is None) != (b is None) or a != b

    def _query(self):
        return self.model.query

    def _query_filter(self, query, expression):
        return query.filter(expression)

    def _expression_for_condition(self, condition):
        return condition.filter.expression(condition.value)

    def _query_filter_by_id(self, query, id):
        try:
            return query.filter(self.id_column == id).one()
        except NoResultFound:
            raise ItemNotFound(self.resource, id=id)

    def _query_order_by(self, query, sort=None):
        order_clauses = []

        if not sort:
            return query.order_by(self.default_sort_expression)

        for field, attribute, reverse in sort:
            column = getattr(self.model, attribute)

            order_clauses.append(column.desc() if reverse else column.asc())

        return query.order_by(*order_clauses)

    def create(self, properties, commit=True):
        item = self.model()

        for key, value in properties.items():
            setattr(item, key, value)

        session = self._get_session()

        try:
            session.add(item)
            if commit:
                session.commit()
        except IntegrityError as e:
            session.rollback()
            return None

        return item

    def update(self, item, changes, commit=True):
        session = self._get_session()

        actual_changes = {
            key: value for key, value in changes.items()
            if self._is_change(get_value(key, item, None), value)
        }

        try:
            for key, value in changes.items():
                setattr(item, key, value)

            if commit:
                session.commit()

        except IntegrityError as e:
            session.rollback()

            if hasattr(e.orig, 'pgcode'):
                if e.orig.code == '23505': # duplicate key
                    raise DuplicateKey(detail=e.orig.diag.message_detail)

            if current_app.debug:
                raise BackendConflict(debug_info=dict(exception_message=str(e),
                                      statement=e.statement,
                                      params=e.params))
            raise BackendConflict()

        return item
