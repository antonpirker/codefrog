
import os

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string

from maintainer.main.utils import run_shell_command
from maintainer.main import metrics
from maintainer.main.models import CodeMetric, ExternalMetric

GIT_BRANCH = 'master'
OUT_DIR = os.path.join(settings.BASE_DIR, os.path.pardir, 'data')

PROJECTS = (
    {
        'slug': 'backend',
        'name': 'donut-backend',
        'source_dir': '/projects/donation/server/django-donut',

        'gitlab_personal_access_token': 'CbCvxtYU-M-U1Pdsyemn',
        'gitlab_group': 'die-gmbh',
        'gitlab_project': 'donation',

        'sentry_auth_token': 'a1f913abcb794e709b8ad8a82b1966e51d10df638b8c4fcc9fd165b25ddaa537',
        'sentry_organization_slug': 'formunauts-gmbh',
        'sentry_project_slug': 'backend-live',
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

    metrics = CodeMetric.objects.filter(
        project_slug=project['slug'],
    ).order_by('date')

    context = {
        'metrics': metrics,
        'project': project,
    }

    rendered = render_to_string('index.html', context=context)
    return HttpResponse(rendered)


def update_issues(request):
    for project in PROJECTS:
        for metric in ExternalMetric.objects.all().order_by('-date'):
            date = metric.date.strftime('%Y-%m-%d')
            gitlab_bug_issues = metrics.gitlab_bug_issues(project, date)
            metric.gitlab_bug_issues = gitlab_bug_issues
            metric.save()
            print('.')

    return HttpResponse('Finished!')


def update_errors(request):
    for project in PROJECTS:
        for errors_per_day in metrics.sentry_errors(project):
            for date_string in errors_per_day.keys():
                ExternalMetric.objects.update_or_create(
                    project_slug=project['slug'],
                    date=date_string,
                    defaults={'sentry_errors': errors_per_day[date_string]},
                )

    return HttpResponse('Finished!')


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

            gitlab_bug_issues = metrics.gitlab_bug_issues(project, version_date)
            jira_bug_issues = metrics.jira_bug_issues(project, version_date)
            sentry_errors = metrics.sentry_errors(project, version_date)

            # save the metric to db
            metric, created = Metric.objects.get_or_create(
                project_slug=project['slug'],
                git_reference=version_name,
                date=version_date,
                complexity=complexity,
                loc=loc,
                gitlab_bug_issues=gitlab_bug_issues,
                jira_bug_issues=jira_bug_issues,
                sentry_errors=sentry_errors,
            )

            # clean up so the next hash can be checked out
            cmd = 'git checkout -q {}'.format(GIT_BRANCH)
            run_shell_command(cmd, cwd=project['source_dir'])

            cmd = 'git clean -q -fd'
            run_shell_command(cmd, cwd=project['source_dir'])
            
            print('.')

    return HttpResponse('Finished!')
