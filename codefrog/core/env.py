import random
from django.core.exceptions import ImproperlyConfigured
from urllib.parse import urlparse


class NoValue(object):
    def __repr__(self):
        return f'{self.__class__.__name__}'


NOTSET = NoValue()


def get_env(*args, **kwargs):
    func = args[0]
    key = args[1]
    try:
        value = func(key, **kwargs)
    except (ImproperlyConfigured, ValueError):
        value = None

    default = kwargs['default'] if 'default' in kwargs else NoValue()
    no_default_set = isinstance(default, NoValue)

    no_value = not value \
        or hasattr(value, 'geturl') and not value.geturl()

    if no_value and no_default_set:
        raise Exception(f'Key {key} not found in environment and no default specified!')

    if no_value:
        if (hasattr(value, 'geturl')
            or type(value) == dict
           ) and default != None:
            value = func(str(random.random()), default=default)
        else:
            value = default

    return value
