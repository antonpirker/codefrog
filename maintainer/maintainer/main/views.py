
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
        project_slug=project['slug'],
    ).order_by('date').values(
        'date',
        'metrics__complexity',
        'metrics__sentry_errors',
        'metrics__gitlab_bug_issues',
        'metrics__number_of_authors',
        'metrics__number_of_commits',
        'metrics__complexity_per_author',
    )

    context = {
        'project': project,
        'metrics': resample(metrics, 'M'),
    }

    rendered = render_to_string('index.html', context=context)
    return HttpResponse(rendered)


def update(request):
    """
    average number of commits per developer per day?
     - number of commits / number of devs
     - or: (number of commits of dev a + number of commits of dev b) / 2

    number of lines changed on the day

    cohesion
    https://en.wikipedia.org/wiki/Cohesion_(computer_science)

    coupling

    design structure matrix
    transitive closure graph
    dependency structure
    DSMs (design structure matrix)
    https://stackoverflow.com/questions/508277/is-there-a-good-dependency-analysis-tool-for-python
    http://furius.ca/snakefood/

    read mood out of commit messages?
    https://stackoverflow.com/questions/933212/is-it-possible-to-guess-a-users-mood-based-on-the-structure-of-text

    """
    for project in PROJECTS:
        print('## PROJECT: %s' % project['name'])
        init_metrics(project)
        update_git_metrics(project)
        #update_sentry_errors(project)
        #update_gitlab_issues(project)

    return HttpResponse('Finished!')


def init_metrics(project):
    print('Starting init_metrics for project %s' % project['name'])

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

    age_in_days = (end_date - start_date).days

    for current_date in (end_date - timedelta(n) for n in range(age_in_days)):
        date_string = current_date.strftime('%Y-%m-%d')

        metric, _ = Metric.objects.get_or_create(
            project_slug=project['slug'],
            date=date_string,
        )
        print('- init %s' % date_string)

    print('Finished init_metrics for project %s' % project['name'])


def update_git_metrics(project):
    print('Starting update_git_metrics for project %s' % project['name'])

    # date of fist commit
    cmd = 'git log --reverse --format="%ad" --date=iso | head -1'
    start_date = parser.parse(run_shell_command(cmd, cwd=project['source_dir']))

    # date of last commit
    cmd = 'git log --format="%ad" --date=iso | head -1'
    end_date = parser.parse(run_shell_command(cmd, cwd=project['source_dir']))

    age_in_days = (end_date - start_date).days

    for current_date in (end_date - timedelta(n) for n in range(age_in_days)):
        date_string = current_date.strftime('%Y-%m-%d')

        # get number of authors of current day
        cmd = 'git log --after="{} 00:00" --before="{} 00:00" ' \
              '--author-date-order --pretty="%ae" --date=iso ' \
              '| sort | uniq | wc -l'.format(
            date_string,
            (current_date + timedelta(days=1)).strftime('%Y-%m-%d'),
        )
        output = run_shell_command(cmd, cwd=project['source_dir'])
        number_of_authors = int(output) if output else None

        # get commits per day:
        cmd = 'git log --after="{} 00:00" --before="{} 00:00" ' \
              '--author-date-order --pretty="%H" | wc -l'.format(
            date_string,
            (current_date + timedelta(days=1)).strftime('%Y-%m-%d'),
        )
        output = run_shell_command(cmd, cwd=project['source_dir'])
        number_of_commits = int(output) if output else None

        # get date and hash of last commit of a day:
        cmd = 'git log --after="{} 00:00" --before="{} 00:00" ' \
              '--author-date-order --pretty="%ad;%H" --date=iso -1'.format(
            current_date.strftime('%Y-%m-%d'),
            (current_date + timedelta(days=1)).strftime('%Y-%m-%d'),
        )
        output = run_shell_command(cmd, cwd=project['source_dir'])
        last_commit_of_day = output.split(';')[1].strip() \
            if output else None

        if last_commit_of_day:
            # checkout the version of the codebase at the given hash
            cmd = 'git checkout -q {}'.format(last_commit_of_day)
            run_shell_command(cmd, cwd=project['source_dir'])

            complexity = metrics.complexity(project['source_dir'])
            loc = metrics.loc(project['source_dir'])

            # save the metric to db
            metric, _ = Metric.objects.get_or_create(
                project_slug=project['slug'],
                date=date_string,
            )
            metric_json = metric.metrics
            if not metric_json:
                metric_json = {}
            metric_json['number_of_authors'] = number_of_authors
            metric_json['number_of_commits'] = number_of_commits
            metric_json['complexity'] = complexity
            metric_json['loc'] = loc
            metric.metrics = metric_json
            metric.save()

            print('- git metrics for %s' % date_string)

            # clean up so the next hash can be checked out
            cmd = 'git checkout -q {}'.format(GIT_BRANCH)
            run_shell_command(cmd, cwd=project['source_dir'])

            cmd = 'git clean -q -fd'
            run_shell_command(cmd, cwd=project['source_dir'])

    print('Finished update_git_metrics for project %s' % project['name'])


def update_sentry_errors(project):
    print('Starting update_sentry_errors for project %s' % project['name'])

    for errors_per_day in metrics.sentry_errors(project):
        for date_string in errors_per_day.keys():
            metric, _ = Metric.objects.get_or_create(
                project_slug=project['slug'],
                date=date_string,
            )

            metric_json = metric.metrics
            if not metric_json:
                metric_json = {}
            metric_json['sentry_errors'] = errors_per_day[date_string]
            metric.metrics = metric_json
            metric.save()

            print('- sentry errors for %s' % date_string)

    print('Finished update_sentry_errors for project %s' % project['name'])


def update_gitlab_issues(project):
    print('Starting update_gitlab_issues for project %s' % project['name'])

    for metric in Metric.objects.all().order_by('-date'):
        date_string = metric.date.strftime('%Y-%m-%d')

        metric_json = metric.metrics
        if not metric_json:
            metric_json = {}
        metric_json['gitlab_bug_issues'] = metrics.gitlab_bug_issues(project, date_string)
        metric.metrics = metric_json
        metric.save()

        print('- git gitlab issues for %s' % date_string)

    print('Finished update_gitlab_issues for project %s' % project['name'])
