# -*- coding: utf-8 -*-

from flask import current_app
from flask_sqlalchemy import get_state
from sqlalchemy.orm import class_mapper
from marshmallow_sqlalchemy import ModelSchema
from .manager import RelationalManager

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
        Base = ModelSchema
        ns = {"Meta": type('Meta', (object,), {"model": model})}
        self.schema_class = type(meta['name']+'Schema', (Base,), ns)

    @staticmethod
    def _get_session():
        return get_state(current_app).db.session

    def _query(self):
        return self.model.query

    def _query_filter(self, query, expression):
        return query.filter(expression)

    def _expression_for_condition(self, condition):
        return condition.filter.expression(condition.value)

    def _query_order_by(self, query, sort=None):
        order_clauses = []

        if not sort:
            return query.order_by(self.default_sort_expression)

        for field, attribute, reverse in sort:
            column = getattr(self.model, attribute)

            order_clauses.append(column.desc() if reverse else column.asc())

        return query.order_by(*order_clauses)
