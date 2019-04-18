import glob
import os


def calculate_complexity(root_dir):
    """
    Calculates the total complexity of the source code in a given directory.

    The complexity is measured by the sum of heading white space on all lines of code.
    """
    complexity = 0

    for filename in glob.iglob(root_dir + '**/**', recursive=True):
        try: 
            with open(os.path.join(filename), 'r') as src:
                for line in src.readlines():
                    complexity += len(line) - len(line.lstrip())
        except (IsADirectoryError, UnicodeDecodeError, FileNotFoundError):
            pass

    return complexity
