
import os

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string

from maintainer.main.utils import run_shell_command
from maintainer.main.metrics import calculate_complexity

GIT_BRANCH = 'master'
OUT_DIR = os.path.join(settings.BASE_DIR, os.path.pardir, 'data')



PROJECTS = (
    {
        'slug': 'backend',
        'source_dir': '/projects/donation/server/django-donut',
    },
#    {
#        'slug': 'frontend',
#        'source_dir': '/projects/donutapp-frontend/src',
#    },
#    {
#        'slug': 'cockpit',
#        'source_dir': '/projects/donut-cockpit/src',
#    },
)


def index(request):
    import ipdb; ipdb.set_trace()
    for project in PROJECTS:
        out_file_name = os.path.join(OUT_DIR, 'metrics-{}.csv'.format(project['slug']))
        with open(out_file_name, 'w') as out_file:
            # checkout desired branch
            cmd = 'git checkout -q {}'.format(GIT_BRANCH)
            run_shell_command(cmd, cwd=project['source_dir'])

            # list all tags in the repo
            cmd = 'git tag'
            versions = run_shell_command(cmd, cwd=project['source_dir']).split()

            for version in versions:
                # extract tag name, hash and date
                cmd = 'git show {} ' \
                      '--no-patch --no-notes --no-standard-notes ' \
                      '--pretty="%H;%ad;%D" --date=iso | grep  "tag:"'.format(version)

                version_detail = run_shell_command(cmd, cwd=project['source_dir']).split(';')
                version_hash = version_detail[0]
                version_date = version_detail[1].split()[0]
                version_name = version_detail[2].replace('\n', '').split()[-1]

                # checkout the version of the codebase at the given hash
                cmd = 'git checkout -q {}'.format(version_hash)
                run_shell_command(cmd, cwd=project['source_dir'])

                # calculate metric of the checked out version
                metric = calculate_complexity(project['source_dir'])

                # save the metric into csv file
                line = [
                    project['slug'],
                    version_date,
                    version_name,
                    str(metric),
                ]
                out_file.write(';'.join(line) + '\n')

                # clean up so the next hash can be checked out
                cmd = 'git checkout -q {}'.format(GIT_BRANCH)
                run_shell_command(cmd, cwd=project['source_dir'])

                cmd = 'git clean -q -fd'
                run_shell_command(cmd, cwd=project['source_dir'])

                print('.')

        # sort the file by date
        cmd = 'sort -o {} {}'.format(out_file_name, out_file_name)
        run_shell_command(cmd, cwd=project['source_dir'])

        print('Finished {}!'.format(project['slug']))


    rendered = render_to_string('index.html')
    return HttpResponse(rendered)
