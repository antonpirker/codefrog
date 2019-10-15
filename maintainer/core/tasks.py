import logging

from celery import shared_task

from core.models import Project
from ingest.tasks.github import update_project_data

logger = logging.getLogger(__name__)


@shared_task
def update_all_projects():
    logger.info('Starting update_all_projects.')

    projects = Project.objects.filter(active=True).order_by('pk')
    for project in projects:
        logger.info(f'Calling update_project_data for project {project.pk}')
        update_project_data.delay(project.pk)

    logger.info('Finished update_all_projects.')
