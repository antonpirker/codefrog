import json
import urllib
from collections import defaultdict

import pytz
import requests
from dateutil import parser

from core.utils import run_shell_command

import logging

from celery import shared_task

from core import garbage
from core.models import Metric, Project

logger = logging.getLogger(__name__)


def dependencies(root_dir):
    """
    Calculate the number of direct and indirect dependencies in the code base,
    as well as the maximum dependency count possible.
    See:
    https://www.youtube.com/watch?time_continue=678&v=tO4OinbOWaE
    (around 12:30 min)

    :param root_dir:
    :return:
    """
    return dependencies_python(root_dir)


def dependencies_python(root_dir):
    """
    Calculate dependencies for a python code base,

    :param root_dir:
    :return:
    """
    cmd = "find {} -type f -name __init__.py | " \
          "awk '{{ print length, $0 }}' | " \
          "sort -n -s | cut -d ' '  -f2 | head -1".format(root_dir)
    output = run_shell_command(cmd)
    python_root_dir = output.replace('__init__.py', '')

    cmd = 'pydeps {} --no-output --show-dot --reverse | ' \
          'grep "\->" | cut -d " " -f5,7 | sort | uniq'.format(python_root_dir)
    output = run_shell_command(cmd)

    dependencies_direct = []
    for item in output.strip().split('\n'):
        dependencies_direct.append(item.strip().split(' '))

    dependencies_indirect = []
    for direct_dependency in dependencies_direct:
        if direct_dependency not in dependencies_indirect:
            dependencies_indirect.append(direct_dependency)

        dep_source = direct_dependency[0]
        dep_target = direct_dependency[1]
        for dep in dependencies_direct:
            if dep[1] == dep_source:
                new_dep = [dep[0], dep_target]
                if new_dep not in dependencies_indirect:
                    dependencies_indirect.append(new_dep)

    everything = dependencies_indirect + dependencies_direct
    modules = sorted(list(set([item for sublist in everything for item in sublist])))

    max_dependencies = len(modules)*len(modules)
    direct_dependencies = len(dependencies_direct)
    indirect_dependencies = len(dependencies_indirect)

    # eigentlich heißt das "density of the network" oder "density of transitive closure graph"
    #  oder "architectual complexity"

    return (
        direct_dependencies, indirect_dependencies, max_dependencies,
    )


def loc(root_dir):
    """
    Calculates the total number of lines of code in the given directory.
    """
    cmd = 'cloc {} -q -csv 2> /dev/null | tail -n +3 | ' \
          'cut --delimiter=, --fields=5 | paste -sd+ - | bc'.format(root_dir)
    loc = run_shell_command(cmd)

    return int(loc or 0)


def gitlab_bug_issues(project, date):
    """
    Returns the number of open issues with label "bug" in Gitlab Issue tracker
    """
    headers = {
        'Private-Token': project['gitlab_personal_access_token'],
    }

    # get the Gitlab group ID
    group_id = 20359
    if not group_id:
        url = 'https://gitlab.com/api/v4/groups?search={}'.format(project['gitlab_group'])
        r = requests.get(url, headers=headers)
        content = json.loads(r.content)
        group_id = content[0]['id']

    # get the Gitlab project ID
    project_id = 28745
    if not project_id:
        url = 'https://gitlab.com/api/v4/groups/{}/projects?search={}'.format(
            group_id, project['gitlab_project']
        )
        r = requests.get(url, headers=headers)
        content = json.loads(r.content)
        project_id = content[0]['id']

    # get all issues for the day
    params = {
        'scope': 'all',
        'created_before': date,
        'labels': 'bug',
    }
    url = 'https://gitlab.com/api/v4/projects/{}/issues?{}'.format(
        project_id, urllib.parse.urlencode(params)
    )
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        raise Exception(r.content)

    content = json.loads(r.content)

    current_date = pytz.utc.localize(parser.parse(date))
    num_issues = 0

    for issue in content:
        created_at = parser.parse(issue['created_at'])
        closed_at = parser.parse(issue['closed_at']) if issue['closed_at'] else None

        if created_at <= current_date and \
            (closed_at == None or closed_at > current_date):
            num_issues += 1

    return num_issues


def sentry_errors(project):
    errors_by_date = defaultdict(int)

    headers = {
        'Authorization': 'Bearer %s' % project['sentry_auth_token'],
    }

    url = 'https://sentry.io/api/0/projects/{}/{}/events/'.format(
        project['sentry_organization_slug'], project['sentry_project_slug']
    )

    while url:
        r = requests.get(url, headers=headers)
        content = json.loads(r.content)

        for event in content:
            if event['type'] == 'error':
                date_created = parser.parse(event['dateCreated'])
                errors_by_date[date_created.strftime('%Y-%m-%d')] += 1

        yield errors_by_date

        url = None
        try:
            links = requests.utils.parse_header_links(r.headers['Link'])
            for link in links:
                if link['rel'] == 'next':
                    url = link['url']
                    break
        except KeyError:
            pass


@shared_task
def import_sentry_errors(project_pk):
    logger.info('Starting import_sentry_errors for project %s', project_pk)
    project = Project.objects.get(pk=project_pk)
    logger.info('Project: %s', project.name)

    for errors_per_day in garbage.sentry_errors(project):
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
        metric_json['gitlab_bug_issues'] = garbage.gitlab_bug_issues(project, date_string)
        metric.metrics = metric_json
        metric.save()

        logger.debug('Gitlab issues for %s for %s', project.name, date_string)

    logger.info('Finished import_gitlab_issues for project %s', project.name)




def old_index_view(request):
    slug = request.GET.get('project', None)
    if not slug:
        project = Project.objects.all().order_by('name').first()
    else:
        project = Project.objects.get(slug=slug)

    today = timezone.now().date()
    last_year = today - timedelta(days=365)

    metrics = Metric.objects.filter(
        project=project,
#        date__gte=last_year,
    ).order_by('date').values(
        'date',
        'metrics__loc',
        'metrics__complexity',
        'metrics__sentry_errors',
        'metrics__gitlab_bug_issues',
        'metrics__github_bug_issues_opened',
        'metrics__github_bug_issues_closed',
        'metrics__github_bug_issues_avg_days_open',
        'metrics__github_bug_issues_now_open',
        'metrics__number_of_commits',
        'metrics__complexity_per_author',
        'metrics__dependencies_direct',
        'metrics__dependencies_indirect',
        'metrics__dependencies_max',
    )

    # Changes in Complexity
    try:
        current_value =  metrics.filter(metrics__complexity__isnull=False)\
            .last()['metrics__complexity'] or 1
    except TypeError:
        current_value = 1

    try:
        value1 = metrics.filter(
            date__lte=today-timedelta(days=1*30),
            metrics__complexity__isnull=False,
        ).order_by('date').last()['metrics__complexity']
    except TypeError:
        value1 = 1
    change1 = (100/(value1 or 1)*current_value-100)/100

    try:
        value2 = metrics.filter(
            date__lte=today-timedelta(days=6*30),
            metrics__complexity__isnull=False,
        ).order_by('date').last()['metrics__complexity']
    except TypeError:
        value2 = 1
    change2 = (100/(value2 or 1)*current_value-100)/100

    try:
        value3 = metrics.filter(
            date__lte=today-timedelta(days=12*30),
            metrics__complexity__isnull=False,
        ).order_by('date').last()['metrics__complexity']
    except TypeError:
        value3 = 1
    change3 = (100/(value3 or 1)*current_value-100)/100

    # Changes in Github Bug Issues Count
    try:
        current_value = metrics.filter(metrics__github_bug_issues_now_open__isnull=False)\
            .last()['metrics__github_bug_issues_now_open'] or 1
    except TypeError:
        current_value = 1

    try:
        value1_1 = metrics.filter(
            date__lte=today-timedelta(days=1*30),
            metrics__github_bug_issues_now_open__isnull=False,
        ).order_by('date').last()['metrics__github_bug_issues_now_open']
    except TypeError:
        value1_1 = 1
    change1_1 = (100 / (value1_1 or 1) * current_value - 100) / 100

    try:
        value1_2 = metrics.filter(
            date__lte=today-timedelta(days=6*30),
            metrics__github_bug_issues_now_open__isnull=False,
        ).order_by('date').last()['metrics__github_bug_issues_now_open']
    except TypeError:
        value1_2 = 1
    change1_2 = (100/(value1_2 or 1)*current_value-100)/100

    try:
        value1_3 = metrics.filter(
            date__lte=today-timedelta(days=12*30),
            metrics__github_bug_issues_now_open__isnull=False,
        ).order_by('date').last()['metrics__github_bug_issues_now_open']
    except TypeError:
        value1_3 = 1
    change1_3 = (100/(value1_3 or 1)*current_value-100)/100

    metric_stats = [{
        'label': 'Complexity: ',
        'value1': '{:+.0%}'.format(change1) if type(change1) == float else change1,
        'value2': '{:+.0%}'.format(change2) if type(change2) == float else change2,
        'value3': '{:+.0%}'.format(change3) if type(change3) == float else change3,
    }, {
        'label': 'GitHub Bug Issues: ',
        'value1': '{:+.0%}'.format(change1_1) if type(change1_1) == float else change1_1,
        'value2': '{:+.0%}'.format(change1_2) if type(change1_2) == float else change1_2,
        'value3': '{:+.0%}'.format(change1_3) if type(change1_3) == float else change1_3,
    }]

    context = {
        'projects': Project.objects.all().order_by('name'),
        'project': project,
        'metrics': resample(metrics, 'W'),
        'metric_stats': metric_stats,
    }

    rendered = render_to_string('index.html', context=context)
    return HttpResponse(rendered)
