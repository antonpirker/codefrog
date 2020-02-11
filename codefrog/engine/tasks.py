import datetime
import logging
import os
from collections import defaultdict

from celery import shared_task

from core.models import Metric, Release, Project
from core.utils import date_range, run_shell_command
from dateutil.parser import parse
from ingest.models import CodeChange, Complexity

logger = logging.getLogger(__name__)


@shared_task
def calculate_code_complexity(project_id):
    logger.info('Project(%s): Starting calculate_code_complexity.', project_id)

    Complexity.objects.filter(project_id=project_id).delete()  # TODO: maybe do this in a better way?

    # Get the newest Complexity we have
    try:
        timestamp = Complexity.objects.filter(project_id=project_id).order_by('-timestamp').first().timestamp
    except AttributeError:
        timestamp = datetime.datetime(1970, 1, 1)

    # List all code change since the newest complexity we have
    code_changes = CodeChange.objects.filter(
        project_id=project_id,
        timestamp__gte=timestamp,
    ).order_by('file_path', 'timestamp')

    complexity = defaultdict(int)
    for change in code_changes:
        # if we do not have a complexity for the file, get the last one from the database.
        if complexity[change.file_path] == 0:
            comp = Complexity.objects.filter(
                project_id=project_id,
                file_path=change.file_path,
                timestamp__lte=change.timestamp,
            ).order_by('-timestamp').first()

            if comp:
                complexity[change.file_path] = comp.complexity

        # add/subtract the complexity of the change.
        complexity[change.file_path] += change.complexity_added
        complexity[change.file_path] -= change.complexity_removed

        # save as new Complexity object.
        Complexity.objects.create(
            project_id=project_id,
            file_path=change.file_path,
            timestamp=change.timestamp,
            complexity=complexity[change.file_path],
        )

    logger.info('Project(%s): Finished calculate_code_complexity.', project_id)
