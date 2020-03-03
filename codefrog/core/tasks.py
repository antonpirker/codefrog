import logging
import os

from django.utils import timezone

from celery import shared_task
from core.models import Project, STATUS_READY
from core.utils import get_file_changes, get_file_ownership, get_file_complexity, SOURCE_TREE_EXCLUDE, log

logger = logging.getLogger(__name__)


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


@shared_task
def get_source_tree_metrics(project_id):
    """
    Walk the entire source tree of the project and calculate the metrics for every file.
    """
    logger.info('Project(%s): Starting get_source_tree_metrics.', project_id)
    log(project_id, 'Calculation fo source tree metrics started')

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning('Project with id %s not found. ', project_id)
        logger.info('Project(%s): Finished (aborted) get_source_tree_metrics.', project_id)
        return

    root = {
        'name': 'root',
        'children': [],
    }

    min_complexity = 0
    max_complexity = 0
    min_changes = 0
    max_changes = 0

    for root_dir, dirs, files in os.walk(project.repo_dir):
        for f in files:
            full_path = os.path.join(root_dir, f)
            if any(x in full_path for x in SOURCE_TREE_EXCLUDE):  # exclude certain directories
                continue
            parts = [part for part in full_path.split(os.sep) if part]
            parts = parts[len(project.repo_dir.split(os.sep)) - 2:]
            current_node = root
            for idx, part in enumerate(parts):
                children = current_node['children']
                node_name = part

                if idx + 1 < len(parts):
                    child_node = {
                        'name': node_name,
                        'children': []
                    }

                    found_child = False
                    for child in children:
                        if child['name'] == node_name:
                            child_node = child
                            found_child = True
                            break

                    if not found_child:
                        children.append(child_node)
                    current_node = child_node

                else:
                    COMPLEXITY_THRESSHOLD = 2000

                    try:
                        complexity = get_file_complexity(full_path)
                    except FileNotFoundError:
                        complexity = 0

                    if complexity < min_complexity:
                        min_complexity = complexity
                    if complexity > max_complexity:
                        max_complexity = complexity

                    if complexity < COMPLEXITY_THRESSHOLD:
                        try:
                            changes = get_file_changes(full_path, project)
                            # TODO: get_file_changes is the only thing that needs CodeChanges.
                            #  Maybe refactore this, that get_file_changes is not calculated on first run, but in another seperate run.
                            #  So the first run is fast and does not have the number of changes, the second run includes then the number of changes.
                        except FileNotFoundError:
                            changes = 0

                        if changes < min_changes:
                            min_changes = changes
                        if changes > max_changes:
                            max_changes = changes

                        repo_link = '{}/blame/master{}'.format(
                            project.github_repo_url,
                            full_path.replace(project.repo_dir, ''),
                        ).replace('//', '/')

                        try:
                            ownership = get_file_ownership(full_path, project)
                        except FileNotFoundError:
                            ownership = []

                        child_node = {
                            'name': node_name,
                            'size': complexity,
                            'changes': changes,
                            'ownership': ownership,
                            # todo: add the owner_color (the color the bubble should have
                            # todo: add owner_name (name of the owner)
                            'repo_link': repo_link,
                            'path': full_path.replace(os.path.join(project.repo_dir, ''), ''),
                        }
                        children.append(child_node)

    project.source_tree_metrics = {
        'tree': root,
        'min_complexity': min_complexity,
        'max_complexity': max_complexity,
        'min_changes': min_changes,
        'max_changes': max_changes,
    }
    project.save()

    logger.info('Project(%s): Finished get_source_tree_metrics.', project_id)
    log(project_id, 'Calculation fo source tree metrics finished')

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
    log(project_id, 'Project import/update finished')

    return project_ids
