import json
from importlib import import_module

import structlog

from connectors.github.utils import check_github_webhook_secret


logger = structlog.get_logger(__name__)


@check_github_webhook_secret
def github_hook(request):
    """
    Receives all Github web hooks and calls the correct handler for web hook.

    :param request: The request as sent by Github.
    :return:
    """
    logger.info('Starting github_hook')
    event = request.headers['X-Github-Event']
    payload = json.loads(request.body)
    action = payload['action']
    logger.info(f'RECEIVED GITHUB HOOK:  {event}/{action}')

    handlers_module = import_module('%s.handlers' % __name__.rpartition('.')[0])
    handler_name = f'{event}__{action}'
    try:
        handler = getattr(handlers_module, handler_name)
        out = handler(payload, request)
    except AttributeError as err:
        msg = f'Could not import handler for Github event: {event} / action: {action}. Error: {err}'
        logger.warning(msg)
        out = msg

    logger.info('Finished github_hook')
    return out
