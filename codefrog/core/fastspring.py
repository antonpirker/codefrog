import logging

import secrets
from django.contrib.auth.models import User

from web.models import UserProfile

logger = logging.getLogger(__name__)


def subscription_activated(payload):
    """
    New account created (and also first charge completed)
    :param payload:
    :return:
    """
    logger.debug('payment.subscription_activated')
    logger.debug('-----------------------------------------------------------')
    logger.debug('payload: %s ' % payload)
    logger.debug('-----------------------------------------------------------')

    fastspring_subscription_id = payload['data']['subscription']
    fastspring_account_id =payload['data']['account']['id']

    first_name = payload['data']['account']['contact']['first']
    last_name = payload['data']['account']['contact']['last']
    email = payload['data']['account']['contact']['email']
    phone = payload['data']['account']['contact']['phone']
    company = payload['data']['account']['contact']['company']

    product = payload['data']['product']['product']  # == 'team-plan-billed-monthly'
    logger.debug("***** %s ******" % first_name)
    logger.debug("***** %s ******" % last_name)

    user, created = User.objects.update_or_create(
        email=email,
        is_staff=False,
        is_active=True,
        is_superuser=False,
        defaults={
            'first_name': first_name,
            'last_name': last_name,
            'password': secrets.token_urlsafe(90),
        },
    )
    user.save()

    logger.info('user: %s' % user)
    logger.info('created: %s' % created)
    profile, created = UserProfile.objects.update_or_create(
        user=user,
        defaults={
            'fastspring_subscription_refid': fastspring_subscription_id,
            'fastspring_account_refid': fastspring_account_id,
        },
    )
    profile.save()
    logger.info('----------------------------')
    logger.info(profile)
    logger.info('----------------------------')
    logger.info(created)
    logger.info('----------------------------')
    logger.info('e')


def subscription_deactivated(payload):
    logger.debug('payment.subscription_deactivated')
    logger.debug('-----------------------------------------------------------')
    logger.debug('payload: %s ' % payload)
    logger.debug('-----------------------------------------------------------')


def subscription_updated(payload):
    logger.debug('payment.subscription_deactivated')
    logger.debug('-----------------------------------------------------------')
    logger.debug('payload: %s ' % payload)
    logger.debug('-----------------------------------------------------------')


# TODO: events to implement:
"""
'subscription.charge.completed' - not fired by the first charge, here subscription_activated is fired. but here a link to a invoice would be great
"""

