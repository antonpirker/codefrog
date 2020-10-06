import os

import structlog
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from core.models import Project, STATUS_READY, SourceNode
from core.utils import get_file_changes, get_file_ownership, get_file_complexity, SOURCE_TREE_EXCLUDE, log, make_one

logger = structlog.get_logger(__name__)


@shared_task
def update_all_projects(*args, **kwargs):
    logger.info('Starting update_all_projects.')

    projects = Project.objects.filter(active=True).order_by('pk')
    for project in projects:
        logger.info(f'Calling update_project for project {project.pk}')
        update_project.delay(project.pk)

    logger.info('Finished update_all_projects.')


@shared_task
def update_project(project_id, *args, **kwargs):
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
def update_source_status_with_metrics(project_id, *args, **kwargs):
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

    with project.get_tmp_repo_dir() as tmp_dir:
        for node in SourceNode.objects.filter(source_status=source_status):
            logger.debug('Project(%s): calculating complexity for %s', project_id, node.path)
            full_path = os.path.join(tmp_dir, node.project_path)
            node.complexity = get_file_complexity(full_path)
            node.ownership = get_file_ownership(full_path, tmp_dir)
            node.changes = get_file_changes(node.project_path, project)
            node.save()

        source_status.active = True
        source_status.save()

        logger.info('Project(%s): Finished update_source_status_with_metrics.', project_id)
        log(project_id, 'Updating complexity of code base', 'stop')

        return project_id


@shared_task
def get_source_status(project_id, *args, **kwargs):
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

    nodes = {}
    with project.get_tmp_repo_dir() as tmp_dir:
        with transaction.atomic():
            with SourceNode.objects.delay_mptt_updates():
                for root_dir, dirs, files in os.walk(tmp_dir):
                    for f in files:
                        path = os.path.join(
                            project.github_repo_name,
                            os.path.join(
                                os.path.join(root_dir, '').replace(os.path.join(tmp_dir, ''), ''),
                                f
                            )
                        )

                        if any(x in path for x in SOURCE_TREE_EXCLUDE):  # exclude certain directories
                            continue

                        path_parts = [part for part in path.split(os.sep) if part]

                        current_node = root
                        for idx, path_part in enumerate(path_parts):
                            node_name = path_part
                            is_leaf_level = idx + 1 >= len(path_parts)
                            if not is_leaf_level:
                                directory_path = '/'.join(path_parts[:idx+1])
                                try:
                                    child_node = nodes[directory_path]
                                except KeyError:
                                    logger.debug('Project(%s): Get or create directory node: %s', project_id, directory_path)
                                    child_node = SourceNode.objects.create(
                                        source_status=source_status,
                                        name=node_name,
                                        path=directory_path,
                                        parent=current_node,
                                    )
                                    nodes[directory_path] = child_node

                                current_node = child_node
                            else:
                                file_path = '/'.join(path_parts)
                                repo_link = project.get_repo_link(os.sep.join(file_path.split(os.sep)[1:])) # remove first directory)
                                logger.debug('Project(%s): Creating file node: %s', project_id, file_path)
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
def save_last_update(project_id, *args, **kwargs):
    logger.info('Project(%s): Starting save_last_update.', project_id)
    project_id = make_one(project_id)

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        return

    project.last_update = timezone.now()
    project.status = STATUS_READY
    project.save(update_fields=['last_update', 'status'])

    logger.info('Project(%s): Finished save_last_update.', project_id)

    return project_id
