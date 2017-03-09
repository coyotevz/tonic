# -*- coding: utf-8 -*-

import sys
from types import MethodType
from collections import OrderedDict
import re

from flask import request
from webargs.flaskparser import parser


HTTP_METHODS = ('GET', 'PUT', 'POST', 'PATCH', 'DELETE')

HTTP_METHOD_VERB_DEFAULTS = {
    'GET': 'read',
    'PUT': 'create',
    'POST': 'create',
    'PATCH': 'update',
    'DELETE': 'destroy',
}

def url_rule_to_uri_pattern(rule):
    return re.sub(r'<(\w+:)?([^>]+)', r'{\2}', rule)

def attribute_to_route_uri(s):
    return s.replace('_', '-')

def to_camel_case(s):
    return s[0].lower() + s.title().replace('_', '')[1:] if s else s


def _method_decorator(method):
    def wrapper(self, *args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            return self.for_method(method, args[0], **kwargs)
        else:
            return lambda f: self.for_method(method, f, *args, **kwargs)

    wrapper.__name__ = method
    return wrapper


class Route(object):

    def __init__(self,
                 method=None,
                 view_func=None,
                 rule=None,
                 attribute=None,
                 rel=None,
                 title=None,
                 description=None,
                 schema=None,
                 response_schema=None,
                 format_response=True):
        self.rel = rel
        self.rule = rule
        self.method = method
        self.attribute = attribute

        self.title = title
        self.description = description

        self.view_func = view_func
        self.format_response = format_response

        self.request_schema = None
        self.response_schema = None

        self._related_routes = ()

        for method in HTTP_METHODS:
            setattr(self, method, MethodType(_method_decorator(method), self))

    @property
    def relation(self):
        if self.rel:
            return self.rel
        else:
            verb = HTTP_METHOD_VERB_DEFAULTS.get(self.method, self.method.lower())
            return to_camel_case("{}_{}".format(verb, self.attribute))

    def schema_factory(self, resource):
        """
        Returns a link schema for a specific resource.
        """
        schema = OrderedDict([
            ("rel", self.relation),
            ("href", url_rule_to_uri_pattern(self.rule_factory(resource, relative=False))),
            ("method", self.method),
        ])

        if self.title:
            schema["title"] = self.title
        if self.description:
            schema["description"] = self.description

        return schema

    def for_method(self,
                   method,
                   view_func,
                   rel=None,
                   title=None,
                   description=None,
                   schema=None,
                   response_schema=None,
                   **kwargs):
        attribute = kwargs.pop('attribute', self.attribute)
        format_response = kwargs.pop('format_response', self.format_response)

        instance = self.__class__(method,
                                  view_func,
                                  rule=self.rule,
                                  rel=rel,
                                  title=title,
                                  description=description,
                                  schema=schema,
                                  response_schema=response_schema,
                                  attribute=attribute,
                                  format_response=format_response,
                                  **kwargs)
        instance._related_routes = self._related_routes + (self,)
        return instance

    def __get__(self, obj, owner):
        if obj is None:
            return self
        return lambda *args, **kwargs: self.view_func.__call__(obj, *args, **kwargs)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(self.rule))

    def rule_factory(self, resource, relative=False):
        """
        Returns a URL rule string for this route and resource.

        :param tonic.Resource resource:
        :param bool relative: whether the rule should be relative to ``resource.route_prefix``
        """
        rule = self.rule

        if rule is None:
            rule = '/{}'.format(attribute_to_route_uri(self.attribute))
        elif callable(rule):
            rule = rule(resource)

        if relative or resource.route_prefix is None:
            return rule[1:]

        return ''.join((resource.route_prefix, rule))

    def view_factory(self, name, resource):
        """
        Returns a view function for all links within this route and resource.

        :param name: Flask view name
        :param tonic.Resource resource:
        """
        request_schema = self.request_schema
        response_schema = self.response_schema
        view_func = self.view_func

        def view(*args, **kwargs):
            print("view ({}, {})".format(args, kwargs))
            instance = resource()
            schema = resource.manager.get_schema(strict=request.method in ['POST', 'PATCH'])
            wargs = parser.parse(schema, request)
            print("parsed wargs: {}".format(wargs))
            #kwargs.update(wargs)
            if wargs:
                args += (wargs,)
            print("new args:", args)
            response = view_func(instance, *args, **kwargs)

            if not self.format_response:
                return response
            return resource.manager.format_response(response)

        return view


def _route_decorator(method):
    @classmethod
    def decorator(cls, *args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            return cls(method, args[0])
        else:
            return lambda f: cls(method, f, *args, **kwargs)

    if sys.version_info.major > 2:
        decorator.__name__ = method
    return decorator


for method in HTTP_METHODS:
    setattr(Route, method, _route_decorator(method))


class RouteSet(object):

    def routes(self):
        return ()
