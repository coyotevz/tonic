from flask import jsonify
from werkzeug.exceptions import Conflict, NotFound, InternalServerError
from werkzeug.http import HTTP_STATUS_CODES

class TonicException(Exception):
    werkzeug_exception = InternalServerError

    @property
    def status_code(self):
        return self.werkzeug_exception.code

    def as_dict(self):
        return {
            'status': self.status_code,
            'message': HTTP_STATUS_CODES.get(self.status_code, '')
        }

    def get_response(self):
        response = jsonify(self.as_dict())
        response.status_code = self.status_code
        return response


class ItemNotFound(TonicException):
    werkzeug_exception = NotFound

    def __init__(self, resource, where=None, id=None):
        super(ItemNotFound, self).__init__()
        self.resource = resource
        self.id = id
        self.where = where

    def as_dict(self):
        dct = super(ItemNotFound, self).as_dict()

        if self.id is not None:
            dct['item'] = {
                "$type": self.resource.meta.name,
                "$id": self.id,
            }

        return dct


class DuplicateKey(TonicException):
    werkzeug_exception = Conflict

    def __init__(self, **kwargs):
        self.data = kwargs


class BackendConflict(TonicException):
    werkzeug_exception = Conflict

    def __init__(self, **kwargs):
        self.data = kwargs

    def as_dict(self):
        dct = super(BackendConflict, self).as_dict()
        dct.update(self.data)
        return dct
