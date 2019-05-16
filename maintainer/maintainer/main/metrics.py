import glob
import json
import os
import urllib
from collections import defaultdict

import pytz
import requests
from dateutil import parser
from dateutil.parser import parse
import pandas as pd
from maintainer.main.utils import run_shell_command


def complexity(root_dir):
    """
    Calculates the total complexity of the source code in a given directory.

    The complexity is measured by the sum of heading white space on all lines of code.
    """
    complexity = 0
    for filename in glob.iglob(os.path.join(root_dir, '**/**'), recursive=True):
        try:
            with open(filename, 'r') as src:
                for line in src.readlines():
                    complexity += len(line) - len(line.lstrip())
        except (IsADirectoryError, UnicodeDecodeError, FileNotFoundError):
            pass

    return complexity


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

    # TODO: eigentlich heißt das "density of the network" oder "density of transitive closure graph"
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


def jira_bug_issues(project, date):
    return None


def github_bug_issues(project):

    GITHUB_API_BASE_URL = 'https://api.github.com'
    GITHUB_API_DEFAULT_HEADERS = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'Maintainer',
    }
    GITHUB_API_DEFAULT_PARAMS = {
        'client_id': os.environ['GITHUB_CLIENT_ID'],
        'client_secret': os.environ['GITHUB_CLIENT_SECRET'],
    }

    GITHUB_BUG_ISSUE_LABELS = [
        'Bug',
        'bug',
        'type:bug/performance',
        'Type: bug',
        'kind/bug',
        'bug', 'debt', 'perf-bloat', 'regression',
        'crash', 'data-loss', 'regression', 'uncaught-exception',
        'regression',
    ]

    github_owner = project.external_services['github']['owner']
    github_repo = project.external_services['github']['repo']
    list_issues_url = f'/repos/{github_owner}/{github_repo}/issues'

    params = GITHUB_API_DEFAULT_PARAMS
    params.update({
        'state': 'all',
        'sort': 'created',
        'direction': 'asc',
        'per_page': '100',
    })

    issues_opened = defaultdict(int)
    issues_closed = defaultdict(int)

    url = f'{GITHUB_API_BASE_URL}{list_issues_url}?%s' % urllib.parse.urlencode(params)

    while url:
        r = requests.get(url, headers=GITHUB_API_DEFAULT_HEADERS)
        content = json.loads(r.content)

        for item in content:
            try:
                labels = [label['name'] for label in item['labels']]
            except TypeError:
                import ipdb; ipdb.set_trace()

            if len(set(labels).intersection(set(GITHUB_BUG_ISSUE_LABELS))) > 0:
                created_at = parse(item['created_at']).date().isoformat()
                closed_at = parse(item['closed_at']).date().isoformat() \
                    if item['closed_at'] else None

                issues_opened[created_at] += 1
                if closed_at:
                    issues_closed[closed_at] += 1

        links = requests.utils.parse_header_links(r.headers['Link'])
        url = None
        for link in links:
            if link['rel'] == 'next':
                url = link['url']
                break

    # Calculate the number of open issues each day
    df1 = pd.DataFrame.from_dict(issues_opened, orient='index')
    df1.columns = ['opened']
    df2 = pd.DataFrame.from_dict(issues_closed, orient='index')
    df2.columns = ['closed']
    df = pd.concat([df1, df2], axis=1, sort=True)
    df['sum_opened'] = df.cumsum()['opened']
    df['now_open'] = df['sum_opened'] - df['closed']
    del df['closed']
    del df['sum_opened']
    df = df.fillna(0)
    issues = df.to_dict('index')

    return issues


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

        next_link_info = r.headers['link'].split(',')[1].split(';')
        if next_link_info[2].strip() == 'results="true"':
            url = next_link_info[0].strip()[1:-1]
        else:
            url = None
