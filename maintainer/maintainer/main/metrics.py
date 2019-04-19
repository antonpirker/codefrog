import glob
import os

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
