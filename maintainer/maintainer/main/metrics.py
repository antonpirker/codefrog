import glob
import os
import urllib
from collections import defaultdict

import requests
import json

from dateutil import parser
import pytz

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


def loc(root_dir):
    """
    Calculates the total number of lines of code in the given directory.
    """
    loc = 0

    cmd = 'cloc {} -q -csv 2> /dev/null | tail -n +3 | ' \
          'cut --delimiter=, --fields=5 | paste -sd+ - | bc'.format(root_dir)
    output = run_shell_command(cmd)

    return int(output or 0)


def jira_bug_issues(project, date):
    return None


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
                print('.')
                date_created = parser.parse(event['dateCreated'])
                errors_by_date[date_created.strftime('%Y-%m-%d')] += 1

        yield errors_by_date

        next_link_info = r.headers['link'].split(',')[1].split(';')
        if next_link_info[2].strip() == 'results="true"':
            url = next_link_info[0].strip()[1:-1]
        else:
            url = None
