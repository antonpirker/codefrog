import subprocess


def run_shell_command(cmd, cwd=None):
    """
    Runs a shell command and returns the commands output as string.
    """
    command = subprocess.run([cmd], cwd=cwd, shell=True, capture_output=True)
    output = command.stdout.decode('utf-8')
    return output
