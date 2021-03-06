# -*- coding: utf-8 -*-

def unpack(value):
    """Return a three tuple of data, code, and headers"""
    if not isinstance(value, tuple):
        return value, 200, {}
    try:
        data, code, headers = value
        return data, code, headers
    except ValueError:
        pass
    try:
        data, code = value
        return data, code, {}
    except ValueError:
        pass
    return value, 200, {}


def get_value(key, obj, default):
    if hasattr(obj, '__getitem__'):
        try:
            return obj[key]
        except (IndexError, TypeError, KeyError):
            pass
    return getattr(obj, key, default)
