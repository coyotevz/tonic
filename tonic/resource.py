# -*- coding: utf-8 -*-

import inspect
from operator import attrgetter
from collections import OrderedDict
from marshmallow.compat import with_metaclass

from .routes import Route


class AttributeDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


def _add_route(routes, route, name):
    if route.attribute is None:
        route.attribute = name

    for r in route._related_routes:
        if r.attribute is None:
            r.attribute = name
        routes[r.relation] = r

    routes[route.relation] = route


class ResourceMeta(type):

    def __new__(cls, name, bases, members):
        new_cls = super(ResourceMeta, cls).__new__(cls, name, bases, members)
        routes = dict(getattr(new_cls, 'routes', {})or {})
        meta = AttributeDict()

        for base in bases:
            meta.update(getattr(base, 'meta', {}) or {})

            for n, m in inspect.getmembers(base, lambda m: isinstance(m, Route)):
                _add_route(routes, m, n)

        if 'Meta' in members:
            opts = members['Meta'].__dict__
            meta.update({k: v for k, v in opts.items()
                         if not k.startswith('__')})
            if not opts.get('name', None):
                meta['name'] = name.lower()
        else:
            meta['name'] = name.lower()

        for n, m in members.items():
            if isinstance(m, Route):
                _add_route(routes, m, n)

            # if isinstance(m, ResourceBound):
            #     m.bind(new_cls)

        # TODO: Honor exclude_routes option

        new_cls.routes = routes
        new_cls.meta = meta
        return new_cls


class Resource(with_metaclass(ResourceMeta, object)):

    api = None
    schema = None
    route_prefix = None

    class Meta:
        name = None
        title = None
        description = None
        exclude_routes = ()
        route_decorators = {}

    @Route.GET('/schema', rel="describedBy", attribute="schema")
    def described_by(self):
        schema = OrderedDict([
            ("$schema", "http://json-schema.org/draft-04/hyper-schema#"),
        ])

        for prop in ('title', 'description'):
            value = getattr(self.meta, prop)
            if value:
                schema[prop] = value

        links = [route for name, route in sorted(self.routes.items())]

        if self.schema:
            schema["type"] = "object"
            schema.update(self.schema.response)

        schema["links"] = [link.schema_factory(self) for link in sorted(links, key=attrgetter('relation'))]

        return schema, 200


class ModelResourceMeta(ResourceMeta):

    def __new__(cls, name, bases, members):
        new_cls = super(ModelResourceMeta, cls).__new__(cls, name, bases, members)

        schema_opts = {}    # Schema options as marshmallow uses
        schema_decls = {}   # Schema fields as marshmallow uses

        for base in bases:
            schema_opts.update(getattr(base, 'schema_opts', {}) or {})
            schema_decls.update(getattr(base, 'schema_decls', {}) or {})

        if 'Schema' in members:
            opts = members['Schema'].__dict__
            schema_decls.update({k: v for k, v in opts.items()
                                 if not k.startswith('__')})

        # schema_opts.update(_extract_schema_options(meta))

        new_cls.schema_opts = schema_opts
        new_cls.schema_decls = schema_decls

        # new_cls.schema_class = _create_schema(name+'Schema',
        #                                      schema_decls,
        #                                      schema_opts)

        return new_cls


class ModelResource(with_metaclass(ModelResourceMeta, Resource)):

    manager = None

    @Route.GET('', rel="instances")
    def instances(self, **kwargs):
        return self.manager.instances(**kwargs)

    instances.request_schema = instances.response_schema = 'collection'

    @instances.POST(rel="create")
    def create(self, properties):
        item = self.manager.create(properties)
        return item

    @Route.GET('/<int:id>', rel="self", attribute="instance")
    def read(self, id):
        return self.manager.read(id)
        return "read {}".format(id)

    @read.PATCH(rel="update")
    def update(self, properties, id):
        return "update {}".format(id)

    @update.DELETE(rel="destroy")
    def destroy(self, id):
        return "destroy {}".format(id)

    class Meta:
        model = None
        id_attribute = None         # use 'id' by default
        sort_attribute = None       # None means use id_attribute for sort
        id_converter = None
        include_id = True
        include_type = False
        filters = True

    class Schema:
        pass
