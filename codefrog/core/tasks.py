import os

from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone

from core.models import Project, STATUS_READY, SourceStatus, SourceNode
from core.utils import get_file_changes, get_file_ownership, get_file_complexity, SOURCE_TREE_EXCLUDE, log, make_one

logger = get_task_logger(__name__)


@shared_task
def update_all_projects():
    logger.info('Starting update_all_projects.')

    projects = Project.objects.filter(active=True).order_by('pk')
    for project in projects:
        logger.info(f'Calling update_project for project {project.pk}')
        update_project.delay(project.pk)

    logger.info('Finished update_all_projects.')


@shared_task
def update_project(project_id):
    logger.info('Project(%s): Starting update_project.', project_id)

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished update_project.', project_id)
        return

    project.update()

    logger.info('Project(%s): Finished update_project.', project_id)

    return project_id


@shared_task
def update_source_status_with_metrics(project_id):
    logger.info('Project(%s): Starting update_source_status_with_metrics.', project_id)
    project_id = make_one(project_id)
    log(project_id, 'Updating complexity of code base', 'start')

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished (aborted) update_source_status_with_metrics.', project_id)
        return

    source_status = project.source_stati.filter(active=False).order_by('timestamp').last()

    if not source_status:
        logger.warning('No inactive SourceStatus found. Aborting.')
        return

    for node in SourceNode.objects.filter(source_status=source_status):
        logger.debug('Project(%s): calculating complexity for %s', project_id, node.path)
        full_path = os.path.join(project.repo_dir, node.path)
        node.complexity = get_file_complexity(full_path)
        node.ownership = get_file_ownership(full_path, project)
        node.changes = get_file_changes(full_path, project)
        node.save()

    source_status.active = True
    source_status.save()

    logger.info('Project(%s): Finished update_source_status_with_metrics.', project_id)
    log(project_id, 'Updating complexity of code base', 'stop')

    return project_id


@shared_task
def get_source_status(project_id):
    logger.info('Project(%s): Starting get_source_status.', project_id)
    project_id = make_one(project_id)
    log(project_id, 'Loading source status of code base', 'start')

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished (aborted) get_source_status.', project_id)
        return

    from core.models import SourceNode, SourceStatus
    source_status = SourceStatus.objects.create(
        project=project,
        timestamp=timezone.now(),
    )

    root = SourceNode.objects.create(
        source_status=source_status,
        name='root',
    )

    for root_dir, dirs, files in os.walk(project.repo_dir):
        for f in files:
            path = os.path.join(root_dir.replace(project.repo_dir, ''), f)

            if any(x in path for x in SOURCE_TREE_EXCLUDE):  # exclude certain directories
                continue
            path_parts = [part for part in path.split(os.sep) if part]

            current_node = root
            for idx, path_part in enumerate(path_parts):
                node_name = path_part

                is_leaf_level = idx + 1 >= len(path_parts)
                if not is_leaf_level:
                    directory_path = '/'.join(path_parts[:idx+1])
                    logger.info('Project(%s): Get or create directory node: %s', project_id, directory_path)
                    child_node, created = SourceNode.objects.get_or_create(
                        source_status=source_status,
                        name=node_name,
                        path=directory_path,
                        parent=current_node,
                    )
                    current_node = child_node
                else:
                    file_path = '/'.join(path_parts)
                    repo_link = project.get_repo_link(file_path)
                    logger.info('Project(%s): Creating file node: %s', project_id, file_path)
                    SourceNode.objects.create(
                        source_status=source_status,
                        parent=current_node,
                        name=node_name,
                        path=file_path,
                        repo_link=repo_link,
                    )

    logger.info('Project(%s): Finished get_source_status.', project_id)
    log(project_id, 'Loading source status of code base', 'stop')

    return project_id


@shared_task
def save_last_update(project_ids):
    logger.info('Project(%s): Starting save_last_update.', project_ids)

    if isinstance(project_ids, int):
        project_ids = [project_ids, ]

    for project_id in project_ids:
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            logger.warning('Project with id %s not found. ', project_id)
            return

        project.last_update = timezone.now()
        project.status = STATUS_READY
        project.save(update_fields=['last_update', 'status'])

    logger.info('Project(%s): Finished save_last_update.', project_ids)

    return project_ids
