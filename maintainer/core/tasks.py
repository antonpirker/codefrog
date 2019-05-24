import logging
import os
import tempfile
import time
from collections import defaultdict
from datetime import timedelta

from dateutil import parser

from celery import shared_task
from core import metrics
from core.models import Metric, Project
from core.utils import run_shell_command

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
    start = time.time()
    logger.info('Starting import_git_metrics for project %s', project_pk)
    project = Project.objects.get(pk=project_pk)

    cmd = 'git checkout -q {}'.format(GIT_BRANCH)
    run_shell_command(cmd, cwd=project.source_dir)

    cmd = 'git clean -q -n'
    run_shell_command(cmd, cwd=project.source_dir)

    cmd = 'git clean -q -f -d'
    run_shell_command(cmd, cwd=project.source_dir)

    def complexityGenerator():
        complexity_added = defaultdict(int)
        complexity_removed = defaultdict(int)
        number_of_commits = defaultdict(int)
        authors = defaultdict(list)

        cmd = 'git log --reverse --author-date-order --pretty="%ad;%H;%aN;%aE" --date=short'
        output = run_shell_command(cmd, cwd=project.source_dir)
        last_day = None
        days = 0
        for line in output.split('\n'):
            if not line:
                continue

            day, git_commit_hash, author_name, author_email = line.split(';')

            number_of_commits[day] += 1
            authors[day].append(f'{author_name} <{author_email}>')

            # lines added
            cmd = f'git config merge.renameLimit 99999 && git show {git_commit_hash} | grep -v "^+++ " | grep "^+"'
            lines_added = run_shell_command(cmd, cwd=project.source_dir)

            for l in lines_added.split('\n'):
                if l:
                    l = l[1:]  # skip first character
                    complexity_added[day] += len(l) - len(l.lstrip())

            # lines removed
            cmd = f'git config merge.renameLimit 99999 && git show {git_commit_hash} | grep -v "^--- " | grep "^-"'
            lines_removed = run_shell_command(cmd, cwd=project.source_dir)

            for l in lines_removed.split('\n'):
                if l:
                    l = l[1:]  # skip first character
                    complexity_removed[day] += len(l) - len(l.lstrip())

            logger.info(
                '%s complexity calculated added/removed for %s: %s / %s',
                project, day, complexity_added[day], complexity_removed[day],
            )

            if last_day != day:
                days += 1

            if days == 30:
                yield (
                    complexity_added,
                    complexity_removed,
                    number_of_commits,
                    authors,
                )
                days = 0

            last_day = day

    complexity_generator = complexityGenerator()

    for (complexity_added, complexity_removed, number_of_commits, authors) in complexity_generator:
        total_added = 0
        total_removed = 0
        for day in sorted(complexity_added.keys()):
            total_added += complexity_added[day]
            total_removed += complexity_removed[day]

            complexity = total_added - total_removed

            # save the metrics to db
            metric, _ = Metric.objects.get_or_create(
                project_id=project_pk,
                date=day,
            )
            metric_json = metric.metrics
            if not metric_json:
                metric_json = {}
            #metric_json['number_of_commits'] = number_of_commits[day]
            metric_json['complexity'] = complexity
            metric.metrics = metric_json
            #metric.authors = authors
            metric.save()
            logger.info(
                '%s: complexity saved %s: %s (%s / %s)',
                project, day, complexity, complexity, number_of_commits[day],
            )

        end = time.time()
        logger.info('import_git_metrics for project %s took %s seconds.', project, end-start)
        logger.info('days processed: %s' % len(complexity_added.keys()))

    return project_pk  # for chaining tasks


@shared_task
def fetch_git_metrics(project_id, source_dir, date):
    date = parser.parse(date)
    date_string = date.strftime('%Y-%m-%d')
    logger.info('Starting fetch_git_metrics for project %s for %s', project_id, date_string)

    # number of commits
    cmd = 'git log --after="{} 00:00" --before="{} 00:00" ' \
          '--author-date-order --pretty="%H" | wc -l'.format(
        date_string,
        (date + timedelta(days=1)).strftime('%Y-%m-%d'),
    )
    output = run_shell_command(cmd, cwd=source_dir)
    number_of_commits = int(output) if output else None

    # list of authors
    cmd = 'git log --after="{} 00:00" --before="{} 00:00" ' \
          '--author-date-order --pretty="%ae" --date=iso ' \
          '| sort | uniq'.format(
        date_string,
        (date + timedelta(days=1)).strftime('%Y-%m-%d'),
    )
    output = run_shell_command(cmd, cwd=source_dir)
    authors = output.strip().split('\n')

    # save the metrics to db
    metric, _ = Metric.objects.get_or_create(
        project_id=project_id,
        date=date_string,
    )
    metric_json = metric.metrics
    if not metric_json:
        metric_json = {}
    metric_json['number_of_commits'] = number_of_commits
    metric.metrics = metric_json
    metric.authors = authors
    metric.save()

    logger.debug(
        'Saved metrics for project %s for %s with id: %s',
        project_id, date_string, metric.pk,
    )
    logger.info('Finished fetch_git_metrics for project %s for %s', project_id, date_string)


@shared_task
def fetch_code_metrics(project_id, source_dir, date, git_commit_hash):
    date = parser.parse(date)
    date_string = date.strftime('%Y-%m-%d')
    logger.info('Starting fetch_code_metrics for project %s for %s', project_id, date_string)

    temp_path = os.path.join(tempfile.gettempdir(), f'maintainer_project_{project_id}')
    temp_path = '/vagrant/tmp'  # TODO: remove
    #logger.warning(f'temp_path: {temp_path}')
    #project_path = os.path.join(temp_path, git_commit_hash)
    #logger.warning(f'source_dir: {source_dir}')
    #logger.warning(f'project_path: {project_path}')

    repo_dir = os.path.join(source_dir, os.path.pardir)

#    if os.path.exists(project_path):
#        shutil.rmtree(project_path)
#    shutil.copytree(repo_dir, project_path)

    # cleanup local directory
    #cmd = 'git clean -q -n'
    #run_shell_command(cmd, cwd=project_path)
    #cmd = 'git clean -q -f -d'
    #run_shell_command(cmd, cwd=project_path)

    # checkout the version of the codebase at the given hash
    cmd = 'git --work-tree={} checkout -q {} -- .'.format(repo_dir, git_commit_hash)
    run_shell_command(cmd, cwd=temp_path)
    logger.warning(git_commit_hash)

    """
    # calculate metrics
    complexity = metrics.complexity(project_path)
    logger.debug('Complexity for project %s: %s', project_id, complexity)

    dependencies = metrics.dependencies(project_path)
    logger.debug('Dependencies for project %s: %s', project_id, dependencies)
    logger.debug('Loc for project %s: %s', project_id, loc)

    # save the metric to db
    metric, _ = Metric.objects.get_or_create(
        project_id=project_id,
        date=date_string,
    )
    metric_json = metric.metrics
    if not metric_json:
        metric_json = {}

    metric_json['complexity'] = complexity
    metric_json['dependencies_direct'] = dependencies[0]
    metric_json['dependencies_indirect'] = dependencies[1]
    metric_json['dependencies_max'] = dependencies[2]
    metric_json['loc'] = loc
    metric.metrics = metric_json

    metric.git_reference = git_commit_hash
    metric.save()

    logger.debug(
        'Saved metrics for project %s for %s with id: %s',
        project_id, date_string, metric.pk,
    )
    """
    logger.info('Finished fetch_code_metrics for project %s for %s', project_id, date_string)


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


@shared_task
def import_github_issues(project_pk):
    logger.info('Starting import_github_issues for project %s' % project_pk)
    project = Project.objects.get(pk=project_pk)
    logger.info('Project: %s' % project.name)

    issues = metrics.github_bug_issues(project)

    if not issues:
        return

    for metric in Metric.objects.filter(project=project).order_by('-date'):
        date_string = metric.date.strftime('%Y-%m-%d')

        try:
            metric_json = metric.metrics
            if not metric_json:
                metric_json = {}
            metric_json['github_bug_issues_opened'] = issues[date_string]['opened']
            metric_json['github_bug_issues_closed'] = issues[date_string]['closed']
            metric_json['github_bug_issues_avg_days_open'] = issues[date_string]['avg_days_open']
            metric_json['github_bug_issues_now_open'] = issues[date_string]['now_open']
            metric.metrics = metric_json
            metric.save()

            logger.info('%s/%s: github metrics: %s / %s | %s / %s',
                project,
                date_string,
                issues[date_string]['opened'],
                issues[date_string]['now_open'],
                issues[date_string]['closed'],
                issues[date_string]['days_open'],
            )

        except KeyError:
            pass

    logger.info('Finished import_github_issues for project %s', project.name)

