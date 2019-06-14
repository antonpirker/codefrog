import logging
import subprocess

import pandas as pd

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
        'github_bug_issues_avg_days_open': 'last',  # avg number of days a issue was open
        'github_bug_issues_now_open': 'last',  # the number of open issues at the end of the week

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

    # Round number of days open
    df['github_bug_issues_avg_days_open'] = df['github_bug_issues_avg_days_open'].round(2)

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
