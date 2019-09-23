import json
from importlib import import_module


def github_hook(request):
    """
    Receives all Github web hooks and calls the correct handler for web hook.

    :param request: The request as sent by Github.
    :return:
    """
    event = request.headers['X-Github-Event']
    payload = json.loads(request.body)
    action = payload['action']

    handlers_module = import_module('%s.handlers' % __name__.rpartition('.')[0])
    handler_name = f'{event}__{action}'
    handler = getattr(handlers_module, handler_name)
    out = handler(payload)
    return out
