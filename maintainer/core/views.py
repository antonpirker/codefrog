import datetime
import json
import secrets

from django.conf import settings
from django.contrib.auth.models import User
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify

from core.decorators import add_user_and_project, only_matching_authenticated_users
from core.models import Metric, Project, Release
from core.utils import get_source_tree_metrics, resample_metrics, resample_releases
from incomingwebhooks.github.utils import get_access_token, \
    get_app_installation_repositories, get_app_installations

MONTH = 30
YEAR = 365

def index(request):
    if request.user.is_authenticated:
        # TODO: this refreshing of the projects could be moved to a special refresh
        # view that is only triggered with a refresh button on top of the list
        # of projects. (flow is similar to toggle of projects)
        installation_id = request.user.profile.github_app_installation_refid
        installation_access_token = get_access_token(installation_id)
        repositories = get_app_installation_repositories(installation_access_token)
        for repository in repositories['repositories']:
            project_slug = slugify(repository['full_name'].replace('/', '-'))
            project, created = Project.objects.get_or_create(
                user=request.user,
                source='github',
                slug=project_slug,
                name=repository['name'],
                git_url=repository['clone_url'],
                defaults={
                    'private': repository['private'],
                },
            )
            print(f'{project}: Created: {created}')

        projects = request.user.projects.all().order_by('-active', 'name')
    else:
        projects = Project.objects.none()

    context = {
        'user': request.user,
        'projects': projects,
        'github_app_client_id': settings.GITHUB_APP_CLIENT_ID,
        'github_redirect_uri': settings.GITHUB_AUTH_REDIRECT_URI,
        'github_state': secrets.token_urlsafe(50),
    }

    if request.user.is_authenticated:
        html = render_to_string('index.html', context=context)
    else:
        html = render_to_string('landing.html', context=context)

    return HttpResponse(html)


def project_detail(request, slug, zoom=None, release_flag=None):
    try:
        project = Project.objects.get(slug=slug)
    except Project.DoesNotExist:
        raise Http404('Project does not exist')

    if project.private:
        if project.user != request.user:
            raise Http404('Project does not exist')

    today = timezone.now()

    # Zoom to desired date range
    zoom = zoom or '1M'
    time_deltas = {
        '1M': datetime.timedelta(days=30 * 1),
        '3M': datetime.timedelta(days=30 * 3),
        '6M': datetime.timedelta(days=30 * 6),
        '1Y': datetime.timedelta(days=365),
        'YTD': datetime.timedelta(days=today.timetuple().tm_yday),
        'ALL': datetime.timedelta(days=365 * 30),
    }
    begin = today - time_deltas.get(zoom, datetime.timedelta(days=30 * 1))

    # Decide what frequency to display the data in.
    days = (today - begin).days

    if 0 < days <= 3 * MONTH:
        frequency = 'D'
    elif 3 * MONTH < days <= 1 * YEAR:
        frequency = 'W'
    elif 1 * YEAR < days <= 3 * YEAR:
        frequency = 'M'
    elif days > 3 * YEAR:
        frequency = 'Q'
    else:  # default
        frequency = 'D'

    # Get metrics in the desired frequency
    metrics = Metric.objects.filter(
        project=project,
        date__gte=begin,
    ).order_by('date').values(
        'date',
        'metrics__complexity',
        'metrics__github_bug_issues_open',
        'metrics__github_other_issues_open',
    )
    if metrics.count() > 0:
        metrics = resample_metrics(metrics, frequency)

    # Get releases in desired frequency
    if release_flag == 'no-releases':
        releases = []
    else:
        releases = Release.objects.filter(
            project=project,
            timestamp__gte=begin,
        ).order_by('timestamp').values(
            'timestamp',
            'name',
        )
        if releases.count() > 0:
            releases = resample_releases(releases, frequency)

    # Source tree metrics
    source_tree_metrics = get_source_tree_metrics(project)

    # Render the HTML and send to client.
    context = {
        'projects': Project.objects.all().order_by('name'),
        'project': project,
        'zoom': zoom,
        'frequency': frequency,
        'show_releases': release_flag != 'no-releases',
        'metrics': metrics,
        'releases': releases,
        'data_tree': json.dumps(source_tree_metrics['tree']),
        'min_complexity': source_tree_metrics['min_complexity'],
        'max_complexity': source_tree_metrics['max_complexity'],
        'min_changes': source_tree_metrics['min_changes'],
        'max_changes': source_tree_metrics['max_changes'],
    }

    html = render_to_string('project/detail.html', context=context)
    return HttpResponse(html)


@only_matching_authenticated_users
def user_settings(request, username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        raise Http404('User does not exist')

    context = {
        'user': user,
        'projects': user.projects.all().order_by('name'),
    }
    html = render_to_string('settings/user.html', context=context)
    return HttpResponse(html)


@only_matching_authenticated_users
@add_user_and_project
def project_settings(request, username, project_slug, user, project):
    context = {
        'project': project,
    }
    html = render_to_string('settings/project.html', context=context)
    return HttpResponse(html)


@only_matching_authenticated_users
@add_user_and_project
def project_toggle(request, username, project_slug, user, project):
    project.active = not project.active
    project.save()

    if project.active:
        project.import_data()

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
