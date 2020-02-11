import datetime
import logging
import os
from collections import defaultdict

from celery import shared_task

from core.models import Metric, Release, Project, Complexity
from core.utils import date_range, run_shell_command
from dateutil.parser import parse
from engine.models import CodeChange

logger = logging.getLogger(__name__)


DAYS_PER_CHUNK = 3650



def get_complexity_change(source_dir, git_commit_hash):
    """

    :param source_dir:
    :param git_commit_hash:
    :return:
    """
    complexity_added = defaultdict(int)
    complexity_removed = defaultdict(int)

    # list files that where changed
    cmd = f'git diff-tree --no-commit-id --name-only -r {git_commit_hash}'
    files_changed = run_shell_command(cmd, cwd=source_dir)

    is_root_commit = not files_changed
    if is_root_commit:
        cmd = f'git diff-tree --root --no-commit-id --name-only -r {git_commit_hash}'
        files_changed = run_shell_command(cmd, cwd=source_dir)

    for file_name in files_changed.split('\n'):
        full_file_name = os.path.join(source_dir, file_name)
        if not file_name or not os.path.exists(full_file_name):
            continue

        # lines added
        # the `|| true` forces a exit code of 0,
        # because grep returns an exit code of 1 if no lines matches.
        cmd = f'git config merge.renameLimit 99999 ' \
            f'&& git diff-tree --no-commit-id -p -r {git_commit_hash} -- "{full_file_name}" ' \
            f'| grep -v "^+++ " | grep "^+" || true'
        lines_added = run_shell_command(cmd, cwd=source_dir)

        for line in lines_added.split('\n'):
            if not line:
                continue

            line = line[1:]  # skip first character
            complexity_added[file_name] += len(line) - len(line.lstrip())

        # lines removed
        # the `|| true` forces a exit code of 0,
        # because grep returns an exit code of 1 if no lines matches.
        cmd = f'git config merge.renameLimit 99999 ' \
            f'&& git diff-tree --no-commit-id -p -r {git_commit_hash} -- "{full_file_name}" ' \
            f'| grep -v "^--- " | grep "^-" || true'
        lines_removed = run_shell_command(cmd, cwd=source_dir)

        for line in lines_removed.split('\n'):
            if not line:
                continue

            line = line[1:]  # skip first character
            complexity_removed[file_name] += len(line) - len(line.lstrip())

    return complexity_added, complexity_removed





