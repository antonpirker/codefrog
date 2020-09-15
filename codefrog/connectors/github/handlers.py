import os
import secrets
import shutil

import structlog
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify
from git import Repo

from connectors.github.utils import create_check_run, get_access_token
from core.models import Project
from core.utils import get_path_complexity, GitHub
from pullrequestbot import checks
from web.models import UserProfile

logger = structlog.get_logger(__name__)

def installation__created(payload, request=None):
    logger.info("### INSTALLATION / CREATED")
    # create a user in our database
    user, created = User.objects.update_or_create(
        username=payload['sender']['login'],
        is_staff=False,
        is_active=True,
        is_superuser=False,
        defaults={
            'password': secrets.token_urlsafe(90),
        },
    )
    profile, created = UserProfile.objects.update_or_create(
        user=user,
        defaults={
            'github_app_installation_refid': payload['installation']['id'],
        },
    )

    installation_id = payload['installation']['id']
    gh = GitHub(installation_id=installation_id)

    # add all repositories to the user
    for repository in payload['repositories']:
        repository_data = gh.get_repository(repository['full_name'])
        project, created = Project.objects.update_or_create(
            user=user,
            source='github',
            slug=slugify(repository_data['full_name'].replace('/', '-')),
            name=repository_data['name'],
            git_url=repository_data['clone_url'],
            defaults={
                'private': repository_data['private'],
            },
        )

        if created:
            project.external_services = {
                'github': {
                    'repository_id': repository['id']
                }
            }
            project.save()

    logger.info("### FINISHED INSTALLATION / CREATED")


def installation__deleted(payload, request=None):
    print("### INSTALLATION / DELETED")


def check_suite__requested(payload, request=None):
    """
    Performs the pull request bot check.

    :param payload:
    :param request:
    :return:
    """
    event = 'check_suite'
    action = 'requested'

    installation_id = payload['installation']['id']
    repository_full_name = payload['repository']['full_name']
    repository_github_id = payload['repository']['id']
    commit_sha_before = payload[event]['before']
    commit_sha_after = payload[event]['after']

    project = checks.get_project_matching_github_hook(payload)

    if not project:
        logger.warning(
            'Project not found for Github web hook for repo %s(%s)',
            repository_full_name,
            repository_github_id,
        )
        return

    installation_access_token = get_access_token(installation_id)

    # Tell Github we queued our check
    check_run_payload = {
        'name': 'Complexity',
        'head_sha': commit_sha_after,
        'status': 'queued',
    }
    create_check_run(repository_full_name, installation_access_token, check_run_payload)

    # Tell Github we started the check
    check_run_payload = {
        'name': 'Complexity',
        'head_sha': commit_sha_after,
        'status': 'in_progress',
    }
    create_check_run(repository_full_name, installation_access_token, check_run_payload)

    # Perform check
    output = checks.perform_complexity_check(
        project=project,
        commit_sha_before=commit_sha_before,
        commit_sha_after=commit_sha_after,
    )

    # Set check to completed and display result
    check_run_payload = {
        'name': 'Complexity',
        'status': 'completed',
        'head_sha': commit_sha_after,
        'details_url': None,
        'conclusion': output['conclusion'],
        'output': {
            'title': output['title'],
            'summary': output['summary'],
        }
    }
    out = create_check_run(repository_full_name, installation_access_token, check_run_payload)

    return out
