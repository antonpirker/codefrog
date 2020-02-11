import datetime
import json
import logging
import urllib

import requests
from celery import shared_task
from dateutil.parser import parse
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from core.models import Metric, Project, Release
from core.utils import date_range, GitHub, run_shell_command
from incomingwebhooks.github.utils import get_access_token
from ingest.models import OpenIssue, Issue

logger = logging.getLogger(__name__)


@shared_task
def import_tags(project_id):
    logger.info(
        'Project(%s): Starting import_tags.',
        project_id,
    )

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished import_github_releases.', project_id)
        return

    cmd = (
        f'git tag --list '
        f'--format "%(refname:strip=2);%(taggerdate);%(committerdate)"'
    )
    output = run_shell_command(cmd, cwd=project.repo_dir)
    tags = [line for line in output.split('\n') if line]

    for tag in tags:
        tag_name, tagger_date, committer_date = tag.split(';')

        try:
            tagger_date = parse(tagger_date)
        except ValueError:
            tagger_date = None

        try:
            committer_date = parse(committer_date)
        except ValueError:
            committer_date = None

        tag_date = tagger_date or committer_date

        logger.debug(
            'Project(%s): Git Tag %s %s',
            project_id,
            tag_name,
            tag_date,
        )
        Release.objects.update_or_create(
            project_id=project_id,
            timestamp=tag_date,
            type='git_tag',
            name=tag_name,
        )

    logger.info('Project(%s): Finished import_tags.', project_id)

    return project_id
