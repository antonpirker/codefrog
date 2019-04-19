import subprocess


def run_shell_command(cmd, cwd=None):
    """
    Runs a shell command and returns the commands output as string.
    """
    command = subprocess.run([cmd], cwd=cwd, shell=True, capture_output=True)
    output = command.stdout.decode('utf-8')
    output_err = command.stderr.decode('utf-8')
    print('')
    print('Output of "%s":' % cmd)
    print(output)
    print('---')
    print(output_err)
    print('---------------------------------------------------')
    return output
