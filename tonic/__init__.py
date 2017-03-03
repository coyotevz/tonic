# -*- coding: utf-8 -*-

from collections import OrderedDict
import operator
import inspect
from six import wraps
from flask import make_response, json, current_app
from werkzeug.wrappers import BaseResponse

from .routes import RouteSet, Route
from .utils import unpack
from .resource import Resource, ModelResource

def _make_response(data, code, headers=None):
    settings = {}
    if current_app.debug:
        settings.setdefault('indent', 4)
        settings.setdefault('sort_keys', True)

    data = json.dumps(data, **settings)

    resp = make_response(data, code)
    resp.headers.extend(headers or {})
    resp.headers['Content-Type'] = 'application/json'
    return resp


class Api(object):

    def __init__(self, app=None, prefix=None, title=None, description=None,
                 default_manager=None):
        self.app = app
        self.blueprint = None
        self.prefix = prefix or ''
        self.title = title
        self.description = description
        self.endpoints = set()
        self.resources = {}
        self.views = []

        self.default_manager = None
        if default_manager is None:
            try:
                from .sqla_manager import SQLAlchemyManager
                self.default_manager = SQLAlchemyManager
            except ImportError:
                pass
        else:
            self.default_manager = default_manager

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        # If app is a blueprint, defer initialization
        try:
            app.record(self._deferred_blueprint_init)
        except AttributeError:
            self._init_app(app)
        else:
            self.blueprint = app

    def _deferred_blueprint_init(self, setup_state):
        self.prefix = ''.join((setup_state.url_prefix or '', self.prefix))

        for resource in self.resources.values():
            resource.route_prefix = ''.join((self.prefix, '/', resource.meta.name))
        self._init_app(setup_state.app)

    def _init_app(self, app):
        app.config.setdefault('TONIC_MAX_PER_PAGE', 100)
        app.config.setdefault('TONIC_DEFAULT_PER_PAGE', 20)

        self._register_view(app,
                            rule=''.join((self.prefix, '/schema')),
                            view_func=self._schema_view,
                            endpoint='schema',
                            methods=['GET'],
                            relation='describedBy')

        for route, resource, view_func, endpoint, methods, relation in self.views:
            rule = route.rule_factory(resource)
            self._register_view(app, rule, view_func, endpoint, methods, relation)
        # TODO: setup error handlers

    def add_route(self, route, resource, endpoint=None, decorator=None):
        endpoint = endpoint or '.'.join((resource.meta.name, route.relation))
        methods = [route.method]
        rule = route.rule_factory(resource)

        view_func = route.view_factory(endpoint, resource)

        if decorator:
            view_func = decorator(view_func)

        if self.app and not self.blueprint:
            self._register_view(self.app, rule, view_func, endpoint, methods, route.relation)
        else:
            self.views.append((route, resource, view_func, endpoint, methods, route.relation))

    def register_resource(self, resource):
        # prevent resources from being added twice
        if resource in self.resources.values():
            return

        if resource.api is not None and resource.api != self:
            raise RuntimeError("Attempted to register a resource that is already registered with a different Api.")

        # check that each model resource has a manager; if not, initialize it.
        if issubclass(resource, ModelResource) and resource.manager is None:
            if self.default_manager:
                resource.manager = self.default_manager(resource, resource.meta.get('model'))
            else:
                raise RuntimeError("'{}' has no manager, fix please."
                                   .format(resource.meta.name))

        resource.api = self
        resource.route_prefix = ''.join((self.prefix, '/', resource.meta.name))

        for route in resource.routes.values():
            route_decorator = resource.meta.route_decorators.get(route.relation, None)
            self.add_route(route, resource, decorator=route_decorator)

        for name, rset in inspect.getmembers(resource, lambda m: isinstance(m, RouteSet)):
            if rset.attribute is None:
                rset.attribute = name
            for i, route in enumerate(rset.routes()):
                if route.attribute is None:
                    route.attribute = '{}_{}'.format(rset.attribute, i)
                resource.routes['{}_{}'.format(rset.attribute, route.relation)] = route
                self.add_route(route, resource)

        self.resources[resource.meta.name] = resource

    def _register_view(self, app, rule, view_func, endpoint, methods, relation):
        view_func = self.output(view_func)
        app.add_url_rule(rule,
                         view_func=view_func,
                         endpoint=endpoint,
                         methods=methods)

    def output(self, view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            resp = view(*args, **kwargs)

            if isinstance(resp, BaseResponse):
                return resp

            data, code, headers = unpack(resp)
            return _make_response(data, code, headers)

        return wrapper

    def _schema_view(self):
        schema = OrderedDict()
        schema["$schema"] = "http://json-schema.org/draft-04/hyper-schema#"

        if self.title:
            schema["title"] = self.title
        if self.description:
            schema["description"] = self.description
        schema["properties"] = properties = OrderedDict([])
        for name, resource in sorted(self.resources.items(), key=operator.itemgetter(0)):
            resource_schema_rule = resource.routes['describedBy'].rule_factory(resource)
            properties[name] = {"$ref": '{}#'.format(resource_schema_rule)}

        return schema, 200
