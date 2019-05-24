import logging
import subprocess

import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


def run_shell_command(cmd, cwd=None):
    """
    Runs a shell command and returns the commands output as string.
    """
    logger.debug(f'Running: {cmd}')
    command = subprocess.run([cmd], cwd=cwd, shell=True, capture_output=True)
    output = command.stdout.strip().decode('utf-8')

    if command.stderr:
        logger.error(f'Error running shell command "{cmd}": {command.stderr}')

    return output


def resample(queryset, frequency):
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

    df['complexity_per_loc'] = df['complexity'] / df['loc']

    df = df.fillna(method='ffill')
    df = df.fillna(0)

    df = df.resample(frequency).agg({
        'loc': 'last',  # take the number of lines of code at the end of the week
        'complexity': 'last',  # take the last complexity in the week
        'complexity_per_loc': 'last',
        'dependencies_direct': 'last',
        'dependencies_indirect': 'last',
        'dependencies_max': 'last',
        'sentry_errors': np.sum,  # sum sentry errors per week
        'gitlab_bug_issues': 'last',  # the number of open issues at the end of the week
        'github_bug_issues_opened': np.sum,  # the total number of issues opened during the week
        'github_bug_issues_closed': np.sum,  # the total number of issues closed during the week
        'github_bug_issues_avg_days_open': 'last',  # avg number of days a issue was open
        'github_bug_issues_now_open': 'last',  # the number of open issues at the end of the week
        'number_of_commits': np.sum,  # sum the number of commits
    })
    df = df.fillna(0)

    df['date'] = df.index
    metrics = df.to_dict('records')
    return metrics
