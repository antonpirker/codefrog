import logging
from datetime import timedelta

from dateutil import parser

from celery import shared_task
from maintainer.main import metrics
from maintainer.main.models import Metric, Project
from maintainer.main.utils import run_shell_command


logger = logging.getLogger(__name__)

GIT_BRANCH = 'master'


@shared_task
def init_project(project_pk):
    logger.info('Starting init_metrics for project %s', project_pk)
    project = Project.objects.get(pk=project_pk)
    logger.info('Project: %s', project.name)

    # checkout desired branch
    cmd = 'git checkout -q {}'.format(GIT_BRANCH)
    run_shell_command(cmd, cwd=project.source_dir)

    # clean up
    cmd = 'git reset --hard'.format(GIT_BRANCH)
    run_shell_command(cmd, cwd=project.source_dir)

    cmd = 'git clean -q -n'
    run_shell_command(cmd, cwd=project.source_dir)

    cmd = 'git clean -q -f -d'
    run_shell_command(cmd, cwd=project.source_dir)

    # remove compiled files.
    cmd = 'find . -name "*.pyc" -delete'
    run_shell_command(cmd, cwd=project.source_dir)

    # date of fist commit
    cmd = 'git log --reverse --format="%ad" --date=iso | head -1'
    start_date = parser.parse(run_shell_command(cmd, cwd=project.source_dir))

    # date of last commit
    cmd = 'git log --format="%ad" --date=iso | head -1'
    end_date = parser.parse(run_shell_command(cmd, cwd=project.source_dir))

    age_in_days = (end_date - start_date).days

    for current_date in (end_date - timedelta(n) for n in range(age_in_days)):
        date_string = current_date.strftime('%Y-%m-%d')

        metric, _ = Metric.objects.get_or_create(
            project=project,
            date=date_string,
        )
        logger.debug('Init %s: %s', project.name, date_string)

    logger.info('Finished init_metrics for project %s', project.name)
    return project_pk  # for chaining tasks


@shared_task
def import_git_metrics(project_pk):
    logger.info('Starting import_git_metrics for project %s', project_pk)
    project = Project.objects.get(pk=project_pk)

    cmd = 'git checkout -q {}'.format(GIT_BRANCH)
    run_shell_command(cmd, cwd=project.source_dir)

    cmd = 'git clean -q -n'
    run_shell_command(cmd, cwd=project.source_dir)

    cmd = 'git clean -q -f -d'
    run_shell_command(cmd, cwd=project.source_dir)

    # date of fist commit
    cmd = 'git log --reverse --format="%ad" --date=iso | head -1'
    start_date = parser.parse(run_shell_command(cmd, cwd=project.source_dir))

    # date of last commit
    cmd = 'git log --format="%ad" --date=iso | head -1'
    end_date = parser.parse(run_shell_command(cmd, cwd=project.source_dir))

    age_in_days = (end_date - start_date).days

    for current_date in (end_date - timedelta(n) for n in range(age_in_days)):
        date_string = current_date.strftime('%Y-%m-%d')

        # get list of authors of current day
        cmd = 'git log --after="{} 00:00" --before="{} 00:00" ' \
              '--author-date-order --pretty="%ae" --date=iso ' \
              '| sort | uniq'.format(
            date_string,
            (current_date + timedelta(days=1)).strftime('%Y-%m-%d'),
        )
        output = run_shell_command(cmd, cwd=project.source_dir)
        authors = output.strip().split('\n')

        # get commits per day:
        cmd = 'git log --after="{} 00:00" --before="{} 00:00" ' \
              '--author-date-order --pretty="%H" | wc -l'.format(
            date_string,
            (current_date + timedelta(days=1)).strftime('%Y-%m-%d'),
        )
        output = run_shell_command(cmd, cwd=project.source_dir)
        number_of_commits = int(output) if output else None

        # get date and hash of last commit of a day:
        cmd = 'git log --after="{} 00:00" --before="{} 00:00" ' \
              '--author-date-order --pretty="%ad;%H" --date=iso -1'.format(
            current_date.strftime('%Y-%m-%d'),
            (current_date + timedelta(days=1)).strftime('%Y-%m-%d'),
        )
        output = run_shell_command(cmd, cwd=project.source_dir)
        last_commit_of_day = output.split(';')[1].strip() \
            if output else None

        if last_commit_of_day:
            logger.debug('Git metrics for %s for %s', project.name, date_string)

            cmd = 'git clean -q -n'
            run_shell_command(cmd, cwd=project.source_dir)

            cmd = 'git clean -q -f -d'
            run_shell_command(cmd, cwd=project.source_dir)

            # checkout the version of the codebase at the given hash
            cmd = 'git checkout -q {}'.format(last_commit_of_day)
            run_shell_command(cmd, cwd=project.source_dir)

            complexity = metrics.complexity(project.source_dir)
            logger.debug('Complexity for %s: %s', project.name, complexity)
            dependencies = metrics.dependencies(project.source_dir)
            logger.debug('Dependencies for %s: %s', project.name, dependencies)
            loc = metrics.loc(project.source_dir)
            logger.debug('Loc for %s: %s', project.name, loc)

            # save the metric to db
            metric, _ = Metric.objects.get_or_create(
                project=project,
                date=date_string,
            )
            metric_json = metric.metrics
            if not metric_json:
                metric_json = {}
            metric_json['number_of_commits'] = number_of_commits
            metric_json['complexity'] = complexity
            metric_json['dependencies_direct'] = dependencies[0]
            metric_json['dependencies_indirect'] = dependencies[1]
            metric_json['dependencies_max'] = dependencies[2]
            metric_json['loc'] = loc
            metric.metrics = metric_json

            metric.git_reference = last_commit_of_day
            metric.authors = authors
            metric.save()

            logger.debug('Saved metrics for %s for %s with id: %s',
                project.name, date_string, metric.pk,
            )

            cmd = 'git checkout -q {}'.format(GIT_BRANCH)
            run_shell_command(cmd, cwd=project.source_dir)

            cmd = 'git clean -q -n'
            run_shell_command(cmd, cwd=project.source_dir)

            cmd = 'git clean -q -f -d'
            run_shell_command(cmd, cwd=project.source_dir)

    logger.info('Finished import_git_metrics for project %s', project.name)
    return project_pk  # for chaining tasks


@shared_task
def import_sentry_errors(project_pk):
    logger.info('Starting import_sentry_errors for project %s', project_pk)
    project = Project.objects.get(pk=project_pk)
    logger.info('Project: %s', project.name)

    for errors_per_day in metrics.sentry_errors(project):
        for date_string in errors_per_day.keys():
            metric, _ = Metric.objects.get_or_create(
                project=project,
                date=date_string,
            )

            metric_json = metric.metrics
            if not metric_json:
                metric_json = {}
            metric_json['sentry_errors'] = errors_per_day[date_string]
            metric.metrics = metric_json
            metric.save()

            logger.debug('Sentry error for %s for %s', project.name, date_string)

    logger.info('Finished import_sentry_errors for project %s', project.name)


@shared_task
def import_gitlab_issues(project_pk):
    logger.info('Starting import_gitlab_issues for project %s' % project_pk)
    project = Project.objects.get(pk=project_pk)
    logger.info('Project: %s' % project.name)

    for metric in Metric.objects.all().order_by('-date'):
        date_string = metric.date.strftime('%Y-%m-%d')

        metric_json = metric.metrics
        if not metric_json:
            metric_json = {}
        metric_json['gitlab_bug_issues'] = metrics.gitlab_bug_issues(project, date_string)
        metric.metrics = metric_json
        metric.save()

        logger.debug('Gitlab issues for %s for %s', project.name, date_string)

    logger.info('Finished import_gitlab_issues for project %s', project.name)
