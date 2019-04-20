
import os
from datetime import timedelta

from dateutil import parser
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from maintainer.main import metrics
from maintainer.main.models import Metric
from maintainer.main.utils import run_shell_command, resample

GIT_BRANCH = 'master'
OUT_DIR = os.path.join(settings.BASE_DIR, os.path.pardir, 'data')

PROJECTS = (
    {
        'slug': 'backend',
        'name': 'donut-backend',
        'source_dir': '/projects/donation/server/django-donut',

        'gitlab_personal_access_token': 'iqZyDH1t7BtjiQHsRssa',
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

    metrics = Metric.objects.filter(
        project_slug=project['slug'],)\
    .order_by('date').values(
            'date',
            'metrics__complexity',
            'metrics__sentry_errors',
            'metrics__gitlab_bug_issues',
    )

    context = {
        'project': project,
        'metrics': resample(metrics, 'W'),
    }

    rendered = render_to_string('index.html', context=context)
    return HttpResponse(rendered)


def update_issues(request):
    for project in PROJECTS:
        for metric in Metric.objects.all().order_by('-date'):
            date = metric.date.strftime('%Y-%m-%d')
            gitlab_bug_issues = metrics.gitlab_bug_issues(project, date)
            metric.gitlab_bug_issues = gitlab_bug_issues

            metric_json = metric.metrics
            if not metric_json:
                metric_json = {}
            metric_json['gitlab_bug_issues'] = gitlab_bug_issues
            metric.metrics = metric_json

            metric.save()
            print('.')

    return HttpResponse('Finished!')


def update_errors(request):
    for project in PROJECTS:
        for errors_per_day in metrics.sentry_errors(project):
            for date_string in errors_per_day.keys():
                metric, _ = Metric.objects.get_or_create(
                    project_slug=project['slug'],
                    date=date_string,
                )

                metric.sentry_errors = errors_per_day[date_string]

                metric_json = metric.metrics
                if not metric_json:
                    metric_json = {}
                metric_json['sentry_errors'] = errors_per_day[date_string]
                metric.metrics = metric_json

                metric.save()

    return HttpResponse('Finished!')

def update(request):
    for project in PROJECTS:
        # checkout desired branch
        cmd = 'git checkout -q {}'.format(GIT_BRANCH)
        run_shell_command(cmd, cwd=project['source_dir'])

        # remove compiled files.
        cmd = 'find . -name "*.pyc" -delete'
        run_shell_command(cmd, cwd=project['source_dir'])

        # date of fist commit
        cmd = 'git log --reverse --format="%ad" --date=iso | head -1'
        start_date = parser.parse(run_shell_command(cmd, cwd=project['source_dir']))

        # date of last commit
        cmd = 'git log --format="%ad" --date=iso | head -1'
        end_date = parser.parse(run_shell_command(cmd, cwd=project['source_dir']))

        age_in_days = (end_date-start_date).days

        for current_date in (end_date - timedelta(n) for n in range(age_in_days)):
            date_string = current_date.strftime('%Y-%m-%d')

            # get date and hash of last commit of a day:
            cmd = 'git log --after="{} 00:00" --before="{} 00:00" --author-date-order --pretty="%ad;%H" --date=iso -1'.format(
                current_date.strftime('%Y-%m-%d'),
                (current_date+timedelta(days=1)).strftime('%Y-%m-%d')
            )
            output = run_shell_command(cmd, cwd=project['source_dir'])
            if output:
                last_commit_of_day = run_shell_command(cmd, cwd=project['source_dir']).split(';')[1].strip()
            else:
                last_commit_of_day = None

            if last_commit_of_day:
                print('Handling %s' % date_string)
                # checkout the version of the codebase at the given hash
                cmd = 'git checkout -q {}'.format(last_commit_of_day)
                run_shell_command(cmd, cwd=project['source_dir'])

                # calculate metric of the checked out version
                complexity = metrics.complexity(project['source_dir'])
                #loc = metrics.loc(project['source_dir'])

                print(' - %s' % complexity)
                # save the metric to db
                Metric.objects.update_or_create(
                    project_slug=project['slug'],
                    date=date_string,
                    defaults={
                        'git_reference': last_commit_of_day,
                        'complexity': complexity,
#                        'loc': loc,
                        'metrics': {
                            'git_reference': last_commit_of_day,
                            'complexity': complexity,
#                            'loc': loc,
                        }
                    },
                )

                # clean up so the next hash can be checked out
                cmd = 'git checkout -q {}'.format(GIT_BRANCH)
                run_shell_command(cmd, cwd=project['source_dir'])

                cmd = 'git clean -q -fd'
                run_shell_command(cmd, cwd=project['source_dir'])

    return HttpResponse('Finished!')
