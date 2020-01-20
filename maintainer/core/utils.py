import datetime
import logging
import os
import jwt
import subprocess
import time
import requests
import json
from datetime import timedelta
from urllib.parse import parse_qs

import pandas as pd

from ingest.models import RawCodeChange

from django.conf import settings

logger = logging.getLogger(__name__)


def run_shell_command(cmd, cwd=None):
    """
    Runs a shell command and returns the commands output as string.
    """
    logger.debug(f'Command: {cmd}')
    try:
        output = subprocess.check_output(cmd, cwd=cwd, shell=True)
    except subprocess.CalledProcessError as err:
        logger.error(f'Non zero exit code running: {err.cmd}')
        output = err.output

    return output.decode('utf-8')


def date_range(start_date, end_date):
    start_date = start_date\
        .replace(hour=0, minute=0, second=0, microsecond=0) \
            if isinstance(start_date, datetime.datetime) else start_date
    end_date = (end_date + timedelta(days=1))\
        .replace(hour=0, minute=0, second=0, microsecond=0) \
            if isinstance(end_date, datetime.datetime) else end_date

    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def get_file_changes(filename, project):
    filename = filename.replace('{}{}'.format(project.repo_dir, os.sep), '')
    return RawCodeChange.objects.filter(
        project=project,
        file_path=filename,
    ).count()


def get_file_ownership(filename, project):
    cmd = f'git shortlog -s -n -e -- {filename}'
    output = run_shell_command(cmd, cwd=project.repo_dir)
    output = [line for line in output.split('\n') if line]

    ownerships = []

    for line in output:
        lines, author = line.lstrip().split('\t')
        ownerships.append({
            'author': author,
            'lines': int(lines),
        })

    top = ownerships[:4]

    others = ownerships[6:]
    lines_of_others = sum([x['lines'] for x in others])

    if len(others) > 0:
        top.append({
            'author': '%s Others' % len(others),
            'lines': lines_of_others,
        })

    # normalize ownership to percentage values
    sum_values = sum([x['lines'] for x in top])
    for x in top:
        x['lines'] = round(x['lines'] / sum_values * 100)

    return top


def get_file_complexity(filename):
    complexity = 0
    with open(filename) as file:
        try:
            for line in file:
                complexity += len(line) - len(line.lstrip())
        except UnicodeDecodeError:
            # TODO: This should only happen for binary files like jpg,
            #  but could be potential a real hard to find bug
            #  if the complexity is always wrong.
            pass

    return complexity


def get_path_complexity(path):
    complexity = 0
    for root_dir, dirs, files in os.walk(path):
        for f in files:
            full_path = os.path.join(root_dir, f)
            if any(x in full_path for x in SOURCE_TREE_EXCLUDE):
                continue
            complexity += get_file_complexity(full_path)

    return complexity


SOURCE_TREE_EXCLUDE = [
    '/.git/',
]


def get_source_tree_metrics(project):
    """
    Walk the entire source tree of the project and calculate the metrics for every file.

    The repository is pulled before so the current state of the repository is used.
    """
    root = {
        'name': 'root',
        'children': [],
    }

    min_complexity = 0
    max_complexity = 0
    min_changes = 0
    max_changes = 0

    project.clone_repo()
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


def resample_metrics(queryset, frequency):
    """
    Resamples the data in queryset to a given frequency

    The strings to specify are the ones of the Pandas library.
    A list of possible strings can be found here:
    https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#dateoffset-objects
    """
    def rename_column(val):
        return val.replace('metrics__', '')

    if len(queryset) == 0:
        return []

    df = pd.DataFrame.from_records(queryset)
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    df = df.rename(rename_column, axis='columns')
    df = df.fillna(method='ffill')
    df = df.fillna(0)

    df = df.resample(frequency).agg({
        'complexity': 'last',  # take the last complexity in the week
        'github_issue_age': 'last',
        'github_issues_open': 'last',

        #'loc': 'last',  # take the number of lines of code at the end of the week
        #'complexity_per_loc': 'last',
        #'dependencies_direct': 'last',
        #'dependencies_indirect': 'last',
        #'dependencies_max': 'last',
        #'sentry_errors': np.sum,  # sum sentry errors per week
        #'gitlab_bug_issues': 'last',  # the number of open issues at the end of the week
        #'github_bug_issues_opened': np.sum,  # the total number of issues opened during the week
        #'github_bug_issues_closed': np.sum,  # the total number of issues closed during the week
        #'number_of_commits': np.sum,  # sum the number of commits
    })
    df = df.fillna(0)

    # Normalize complexity value to between 0..1 and round to 2 decimals
    #df['complexity'] = (df['complexity'] - df['complexity'].min()) / \
    #                   (df['complexity'].max() - df['complexity'].min())
    df['complexity'] = df['complexity'].round(2)

    df = df.fillna(0)
    df['date'] = df.index
    metrics = df.to_dict('records')
    return metrics


def resample_releases(queryset, frequency):
    df = pd.DataFrame.from_records(queryset)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')

    df = df.resample(frequency).agg({
        'name': 'last',
    })

    df['timestamp'] = df.index

    # remove NaN rows
    df = df[pd.notnull(df['name'])]

    releases = df.to_dict('records')
    return releases



class GitHub:
    """
    Client to Github API
    """
    api_base_url = 'https://api.github.com'

    user_access_token = None
    installation_access_token = None

    def __init__(self, installation_id=None, code=None, state=None):
        logger.info(f'---> GitHub __init__ installation_id={installation_id}, code={code}, state={state}')
        if not self.installation_access_token and installation_id:
            self.installation_access_token = self.get_access_token(installation_id)

        if not self.user_access_token and code and state:
            self.user_access_token = self._get_user_access_token(code, state)

    @staticmethod
    def _get_user_access_token(code, state):
        logger.info(f'---> GitHub _get_user_access_token code={code}, state={state}')
        api_url = f'https://github.com/login/oauth/access_token'

        payload = {
            'client_id': settings.GITHUB_APP_CLIENT_ID,
            'client_secret': settings.GITHUB_APP_CLIENT_SECRET,
            'redirect_url': settings.GITHUB_AUTH_REDIRECT_URI,
            'code': code,
            'state': state,
        }

        out = requests.post(api_url, data=payload)
        data = parse_qs(out.content.decode())
        user_access_token = data['access_token'][0]

        return user_access_token

    def _get(self, url, headers=None):
        logger.info(f'---> GitHub _get url={url}')
        api_url = f'{self.api_base_url}{url}'

        if not headers:
            headers = {
                'Authorization': 'token %s' % self.installation_access_token,
            }

        out = requests.get(api_url, headers=headers)
        return json.loads(out.content)

    def _post(self, url, headers=None):
        logger.info(f'---> GitHub _post url={url}')
        api_url = f'{self.api_base_url}{url}'

        out = requests.post(api_url, headers=headers)
        return json.loads(out.content)

    def create_jwt(self):
        logger.info(f'---> GitHub create_jwt')
        """
        Generate a JSON web token (JWT)
        """
        private_key = settings.GITHUB_PRIVATE_KEY.decode("utf-8")
        current_time = int(time.time())

        payload = {
            'iat': current_time,  # issued at time
            'exp': current_time + (10 * 60),  # JWT expiration time (10 minute maximum)
            'iss': settings.GITHUB_APP_IDENTIFIER,  # GitHub App's identifier
        }

        token = jwt.encode(payload, private_key, algorithm='RS256').decode("utf-8")
        return token

    def get_access_token(self, installation_id):
        logger.info(f'---> GitHub get_access_token installation_id={installation_id}')
        """
        Authenticate as a Github App and get an installation access token.
        """
        url = f'/app/installations/{installation_id}/access_tokens'

        headers = {
            'Accept': 'application/vnd.github.machine-man-preview+json',
            'Authorization': 'Bearer %s' % self.create_jwt(),
        }

        out = self._post(url, headers=headers)
        token = out['token']
        print("Installation access token: %s" % token)

        return token

    def get_repository(self, repository_full_name):
        logger.info(f'---> GitHub get_repository repository_full_name={repository_full_name}')
        url = f'/repos/{repository_full_name}'

        return self._get(url)

    def get_user(self):
        logger.info(f'---> GitHub get_user')
        url = f'/user'

        if not self.user_access_token:
            return None

        headers = {
            'Authorization': 'token %s' % self.user_access_token,
        }

        return self._get(url, headers=headers)

    def get_installation_repositories(self, installations_id):
        url = f'/user/installations/{installations_id}/repositories'

        headers = {
            'Accept': 'application/vnd.github.machine-man-preview+json',
            'Authorization': 'token %s' % self.user_access_token,
        }

        return self._get(url, headers=headers)
