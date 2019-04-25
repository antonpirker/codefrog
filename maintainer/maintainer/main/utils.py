import subprocess

import numpy as np
import pandas as pd


def run_shell_command(cmd, cwd=None):
    """
    Runs a shell command and returns the commands output as string.
    """
    command = subprocess.run([cmd], cwd=cwd, shell=True, capture_output=True)
    output = command.stdout.decode('utf-8')
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

    df = pd.DataFrame.from_records(queryset)
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    df = df.rename(rename_column, axis='columns')

    df = df.resample(frequency).agg({
        'complexity': 'last',  # take the last complexity in the week
        'sentry_errors': np.sum,  # sum sentry errors per week
        'gitlab_bug_issues': 'last',  # the number of open issues at the end of the week
        'number_of_authors': np.average,  # this is wrong!
        'number_of_commits': np.sum,  # number of commits
    })

    df['date'] = df.index
    df = df.fillna(0)
    metrics = df.to_dict('records')

    return metrics
