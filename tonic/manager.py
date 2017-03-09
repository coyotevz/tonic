# -*- coding: utf-8 -*-

from marshmallow.utils import is_collection
from webargs.flaskparser import parser

class Manager(object):

    def __init__(self, resource, model):
        self.resource = resource
        self.filters = {}
        self.schema_class = None

        # attach manager to the resource
        resource.manager = self

        self._init_model(resource, model, resource.meta)
        self._init_schema(resource, model, resource.meta)
        self._init_filters(resource, resource.meta)

    def _init_model(self, resource, model, meta):
        self.model = model

    def _init_schema(self, resource, model, meta):
        pass

    def _init_filters(self, resource, meta):
        # FIXME: Implement this
        self.filters = {}

    # Override by implementors

    @property
    def schema(self):
        return self.schema_class()

    def relation_instances(self, item, attribute, target_resource,
                           page=None, per_page=None):
        raise NotImplementedError()

    def relation_add(self, item, attribute, target_resource, target_item):
        raise NotImplementedError()

    def relation_remove(self, item, attribute, target_resource, target_item):
        raise NotImplementedError()

    def paginated_instances(self, page, per_page, where=None, sort=None):
        pass

    def instances(self, where=None, sort=None):
        pass

    def first(self, where=None, sort=None):
        try:
            return self.instances(where, sort)[0]
        except IndexError:
            raise ItemNotFound(self.resource, where=where)

    def create(self, properties, commit=True):
        pass

    def read(self, id):
        pass

    def update(self, item, changes, commit=True):
        pass

    def delete(self, item):
        pass

    def delete_by_id(self, id):
        return self.delete(self.read(id))

    def commit(self):
        pass

    def verify(self, properties, partial=False):
        pass

    # Experimental api

    def parse_request(self, request):
        data = request.json

        if not data and request.method in ('GET', 'HEAD'):
            data = dict(request.args)

        return data

    def format_response(self, response):
        many = is_collection(response)
        return self.schema.dump(response, many=many).data


class RelationalManager(Manager):

    def _query(self):
        raise NotImplementedError()

    def _query_filter(self, query, expression):
        raise NotImplementedError()

    def _query_filter_by_id(self, query, id):
        raise NotImplementedError()

    def _expression_for_join(self, attribute, expression):
        raise NotImplementedError()

    def _expression_for_ids(self, ids):
        raise NotImplementedError()

    def _expression_for_condition(self, condition):
        raise NotImplementedError()

    def _or_expression(self, expressions):
        raise NotImplementedError()

    def _and_expression(self, expressions):
        raise NotImplementedError()

    def _query_order_by(self, query, sort=None):
        raise NotImplementedError()

    def _query_get_paginated_items(self, query, page, per_page):
        raise NotImplementedError()

    def _query_get_all(self, query):
        raise NotImplementedError()

    def _query_get_on(self, query):
        raise NotImplementedError()

    def _query_get_first(self, query):
        raise NotImplementedError()

    def paginated_instances(self, page, per_page, where=None, sort=None):
        instances = self.instances(where=where, sort=sort)
        return self._query_get_paginated_instances(instances, page, per_page)

    def instances(self, where=None, sort=None):
        query = self._query()

        if query is None:
            return []

        if where:
            expressions = [self._expression_for_condition(condition) for condition in where]
            query = self._query_filter(query, self._and_expression(expressions))

        return self._query_order_by(query, sort)

    def first(self, where=None, sort=None):
        try:
            return self._query_get_first(self.instances(where, sort))
        except IndexError:
            raise ItemNotFound(self.resource, where=where)

    def read(self, id):
        query = self._query()

        if query is None:
            raise ItemNotFound(self.resource, id=id)
        return self._query_filter_by_id(query, id)
