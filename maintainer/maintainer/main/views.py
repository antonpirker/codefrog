
import os

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string

from maintainer.main.utils import run_shell_command
from maintainer.main import metrics
from maintainer.main.models import Metric

GIT_BRANCH = 'master'
OUT_DIR = os.path.join(settings.BASE_DIR, os.path.pardir, 'data')

PROJECTS = (
    {
        'slug': 'backend',
        'name': 'donut-backend',
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
    """
    Displays one project.
    """
    DONUT_BACKEND = 0
    project = PROJECTS[DONUT_BACKEND]

    metrics = Metric.objects.filter(
        project_slug=project['slug'],
    ).order_by('date')

    context = {
        'metrics': metrics,
        'project': project,
    }

    rendered = render_to_string('index.html', context=context)
    return HttpResponse(rendered)

def update(request):
    for project in PROJECTS:
        # checkout desired branch
        cmd = 'git checkout -q {}'.format(GIT_BRANCH)
        run_shell_command(cmd, cwd=project['source_dir'])

        # remove compiled files.
        cmd = 'find . -name "*.pyc" -delete'
        run_shell_command(cmd, cwd=project['source_dir'])

        # list all tags in the repo
        cmd = 'git log --no-walk --tags --pretty="%H;%ad;%D" --date=iso'
        versions = run_shell_command(cmd, cwd=project['source_dir']).split('\n')

        for version in versions:
            # extract tag name, hash and date
            version_detail = version.split(';')
            version_hash = version_detail[0]
            version_date = version_detail[1].split()[0]
            version_name = version_detail[2].replace('\n', '').split()[-1]

            # checkout the version of the codebase at the given hash
            cmd = 'git checkout -q {}'.format(version_hash)
            run_shell_command(cmd, cwd=project['source_dir'])

            # calculate metric of the checked out version
            complexity = metrics.complexity(project['source_dir'])
            loc = metrics.loc(project['source_dir'])

            # save the metric to db
            metric, created = Metric.objects.get_or_create(
                project_slug=project['slug'],
                git_reference=version_name,
                date=version_date,
                complexity=complexity,
                loc=loc,
            )

            # clean up so the next hash can be checked out
            cmd = 'git checkout -q {}'.format(GIT_BRANCH)
            run_shell_command(cmd, cwd=project['source_dir'])

            cmd = 'git clean -q -fd'
            run_shell_command(cmd, cwd=project['source_dir'])
            
            print('.')

    return HttpResponse('Finished!')
