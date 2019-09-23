import json
from importlib import import_module

from incomingwebhooks.github.utils import check_github_webhook_secret


@check_github_webhook_secret
def github_hook(request):
    """
    Receives all Github web hooks and calls the correct handler for web hook.

    :param request: The request as sent by Github.
    :return:
    """
    event = request.headers['X-Github-Event']
    payload = json.loads(request.body)
    action = payload['action']
    print(f'RECEIVED GITHUB HOOK:  {event}/{action}')

    handlers_module = import_module('%s.handlers' % __name__.rpartition('.')[0])
    handler_name = f'{event}__{action}'
    try:
        handler = getattr(handlers_module, handler_name)
        out = handler(payload)
    except AttributeError:
        out = f'Unknown! Github event: {event} / action: {action}'

    return out
