import datetime
import json
import os
import subprocess
import time
import urllib
from datetime import timedelta
from urllib.parse import parse_qs

import jwt
import numpy as np
import pandas as pd
import requests
import structlog
from dateutil.parser import parse
from django.conf import settings
from django.utils import timezone

from engine.models import CodeChange

logger = structlog.get_logger(__name__)


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


def get_file_changes(filename, project, days=30):
    ref_date = timezone.now() - timedelta(days=days)
    ref_date = ref_date.replace(hour=0, minute=0, second=0, microsecond=0)

    filename = filename.replace('{}{}'.format(project.repo_dir, os.sep), '')
    return CodeChange.objects.filter(
        project=project,
        file_path=filename,
        timestamp__gte=ref_date,
    ).count() or 1


def get_file_ownership(filename, project):
    cmd = f'git shortlog --summary --numbered --email HEAD -- "{filename}"'
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
    complexity = 1
    try:
        with open(filename) as file:
            try:
                for line in file:
                    complexity += len(line) - len(line.lstrip())
            except UnicodeDecodeError:
                # TODO: This should only happen for binary files like jpg,
                #  but could be potential a real hard to find bug
                #  if the complexity is always wrong.
                pass
    except (IsADirectoryError, FileNotFoundError):
        pass

    return complexity


def get_path_complexity(path):
    complexity = 1
    for root_dir, dirs, files in os.walk(path):
        for f in files:
            full_path = os.path.join(root_dir, f)
            if any(x in full_path for x in SOURCE_TREE_EXCLUDE):
                continue
            complexity += get_file_complexity(full_path)

    return complexity


SOURCE_TREE_EXCLUDE = [
    '/.git/',
    'package-lock.json',
]

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
        'github_issues_closed': np.sum,

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


def log(project_id, message, event):
    """
    Add log entry to project.
    """
    from core.models import LogEntry

    if type(project_id) == list:
        project_ids = list(set(project_id))
    else:
        project_ids = (project_id, )

    for project_id in project_ids:
        if event == 'start':
            LogEntry.objects.create(
                project_id=project_id,
                timestamp_start=timezone.now(),
                timestamp_end=None,
                message=message,
            )

        if event == 'stop':
            LogEntry.objects.filter(
                project_id=project_id,
                message=message,
                timestamp_end__isnull=True,
            ).update(
                timestamp_end=timezone.now(),
            )


class GitHub:
    """
    Client to Github API
    """
    api_base_url = 'https://api.github.com'

    GITHUB_ITEMS_PER_PAGE = 100

    user_access_token = None
    installation_access_token = None

    def __init__(self, installation_id=None, code=None, state=None):
        logger.debug(f'---> GitHub __init__ installation_id={installation_id}, code={code}, state={state}')
        if not self.installation_access_token and installation_id:
            self.installation_access_token = self.get_access_token(installation_id)

        if not self.user_access_token and code and state:
            self.user_access_token = self._get_user_access_token(code, state)

    @staticmethod
    def _get_user_access_token(code, state):
        logger.debug(f'---> GitHub _get_user_access_token code={code}, state={state}')
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
        logger.debug(f'---> GitHub _get url={url}')
        api_url = f'{self.api_base_url}{url}'

        if not headers:
            headers = {
                'Authorization': 'token %s' % self.installation_access_token,
            }

        out = requests.get(api_url, headers=headers)
        return json.loads(out.content)

    def _post(self, url, headers=None):
        logger.debug(f'---> GitHub _post url={url}')
        api_url = f'{self.api_base_url}{url}'

        out = requests.post(api_url, headers=headers)
        return json.loads(out.content)

    def create_jwt(self):
        logger.debug(f'---> GitHub create_jwt')
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
        logger.debug(f'---> GitHub get_access_token installation_id={installation_id}')
        """
        Authenticate as a Github App and get an installation access token.
        """
        url = f'/app/installations/{installation_id}/access_tokens'

        headers = {
            'Accept': 'application/vnd.github.machine-man-preview+json',
            'Authorization': 'Bearer %s' % self.create_jwt(),
        }

        out = self._post(url, headers=headers)
        token = out.get('token', None)

        if not token:
            logger.warn(f'Could not get access token for installation id {installation_id}: {out}')

        return token

    def get_repository(self, repository_full_name):
        logger.debug(f'---> GitHub get_repository repository_full_name={repository_full_name}')
        url = f'/repos/{repository_full_name}'

        return self._get(url)

    def get_user(self):
        logger.debug(f'---> GitHub get_user')
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

    def get_issues(self, repo_owner, repo_name, start_date=None):
        params = {
            'state': 'all',
            'sort': 'created',
            'direction': 'asc',
            'per_page': str(self.GITHUB_ITEMS_PER_PAGE),
        }

        if start_date:
            if isinstance(start_date, str):
                start_date = parse(start_date)

            params['since'] = start_date.isoformat()

        return self._get_issues(repo_owner, repo_name, params)

    def get_open_issues(self, repo_owner, repo_name, start_date=None):
        params = {
            'state': 'open',
            'sort': 'created',
            'direction': 'asc',
            'per_page': str(self.GITHUB_ITEMS_PER_PAGE),
        }

        if start_date:
            if isinstance(start_date, str):
                start_date = parse(start_date)

            params['since'] = start_date.isoformat()

        return self._get_issues(repo_owner, repo_name, params)

    def _get_issues(self, repo_owner, repo_name, params):
        headers = {
            'Accept': 'application/vnd.github.machine-man-preview+json',
            'Authorization': 'token %s' % self.installation_access_token,
        }

        list_issues_url = f'/repos/{repo_owner}/{repo_name}/issues'
        url = f'{self.api_base_url}{list_issues_url}?%s' % urllib.parse.urlencode(params)

        retries = 0

        while url:
            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                if retries < 5:
                    time.sleep(1)
                    retries += 1
                    continue

            if retries == 5:
                return

            issues = json.loads(r.content)
            for issue in issues:
                yield issue

            # get url of next page (if any)
            url = None
            try:
                links = requests.utils.parse_header_links(r.headers['Link'])
                for link in links:
                    if link['rel'] == 'next':
                        url = link['url']
                        retries = 0
                        break
            except KeyError:
                pass

    def get_releases(self, repo_owner, repo_name):
        headers = {
            'Accept': 'application/vnd.github.machine-man-preview+json',
            'Authorization': 'token %s' % self.installation_access_token,
        }

        params = {}

        list_releases_url = f'/repos/{repo_owner}/{repo_name}/releases'
        url = f'{self.api_base_url}{list_releases_url}?%s' % urllib.parse.urlencode(params)

        retries = 0

        while url:
            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                if retries < 5:
                    time.sleep(1)
                    retries += 1
                    continue

            if retries == 5:
                return

            releases = json.loads(r.content)
            for release in releases:
                yield release

            # get url of next page (if any)
            url = None
            try:
                links = requests.utils.parse_header_links(r.headers['Link'])
                for link in links:
                    if link['rel'] == 'next':
                        url = link['url']
                        retries = 0
                        break
            except KeyError:
                pass

    def get_pull_requests(self, repo_owner, repo_name):
        params = {
            'state': 'closed',
            'sort': 'updated',
            'direction': 'desc',
            'per_page': str(self.GITHUB_ITEMS_PER_PAGE),
        }

        return self._get_pull_requests(repo_owner, repo_name, params)

    def _get_pull_requests(self, repo_owner, repo_name, params):
        headers = {
            'Accept': 'application/vnd.github.machine-man-preview+json',
            'Authorization': 'token %s' % self.installation_access_token,
        }

        list_pull_requests_url = f'/repos/{repo_owner}/{repo_name}/pulls'
        url = f'{self.api_base_url}{list_pull_requests_url}?%s' % urllib.parse.urlencode(params)

        retries = 0

        while url:
            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                if retries < 5:
                    time.sleep(1)
                    retries += 1
                    continue

            if retries == 5:
                return

            items = json.loads(r.content)
            for item in items:
                yield item

            # get url of next page (if any)
            url = None
            try:
                links = requests.utils.parse_header_links(r.headers['Link'])
                for link in links:
                    if link['rel'] == 'next':
                        url = link['url']
                        retries = 0
                        break
            except KeyError:
                pass


def make_one(list_or_value):
    if type(list_or_value) == list:
        return list(set(list_or_value)) [0]
    else:
        return list_or_value
