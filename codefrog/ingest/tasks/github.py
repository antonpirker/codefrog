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
from engine.models import Issue, OpenIssue

logger = logging.getLogger(__name__)


@shared_task
def update_project_data(project_id):
    logger.info('Project(%s): Starting update_project_data.', project_id)

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished update_project_data.', project_id)
        return

    project.update_data()

    logger.info('Project(%s): Finished update_project_data.', project_id)
