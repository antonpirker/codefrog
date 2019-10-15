import logging

from celery import shared_task

from core.models import Project
from ingest.tasks.github import import_open_github_issues

logger = logging.getLogger(__name__)


@shared_task
def import_all_open_github_issues():
    logger.info('Starting import_all_open_github_issues.')

    projects = Project.objects.filter(source='github', active=True).order_by('pk')
    for project in projects:
        logger.info(f'Calling import_open_github_issues for project {project.pk}')
        import_open_github_issues.delay(
            project.pk,
            project.github_repo_owner,
            project.github_repo_name,
        )

    logger.info('Finished import_all_open_github_issues.')
