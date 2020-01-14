import datetime
import json
import os
import secrets

from django.conf import settings
from django.contrib.auth.models import User
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import RequestContext
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify


from core.decorators import add_user_and_project, only_matching_authenticated_users
from core.models import Metric, Project, Release, UserProfile, Usage
from core.utils import resample_metrics, resample_releases
from incomingwebhooks.github.utils import get_access_token, \
    get_app_installation_repositories

MONTH = 30
YEAR = 365

def index(request):
    projects = Project.objects.none()

    if request.user.is_authenticated and not request.user.is_superuser:
        # TODO: this refreshing of the projects could be moved to a special refresh
        #  view that is only triggered with a refresh button on top of the list
        #  of projects. (flow is similar to toggle of projects)
        installation_id = request.user.profile.github_app_installation_refid
        if installation_id:
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

        projects = request.user.projects.all().order_by('-active', 'name')

    context = {
        'user': request.user,
        'projects': projects,
        'github_app_client_id': settings.GITHUB_APP_CLIENT_ID,
        'github_redirect_uri': settings.GITHUB_AUTH_REDIRECT_URI,
        'github_state': secrets.token_urlsafe(50),
    }

    if request.user.is_authenticated:
        Usage.objects.create(
            user=request.user if request.user.is_authenticated else None,
            project_id=None,
            timestamp=datetime.datetime.utcnow(),
            action='repository_list.view',
        )

        html = render_to_string('index.html', context=context, request=request)
    else:
        Usage.objects.create(
            user=request.user if request.user.is_authenticated else None,
            project_id=None,
            timestamp=datetime.datetime.utcnow(),
            action='landing_page.view',
        )

        html = render_to_string('landing.html', context=context, request=request)

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
    if not zoom:
        if release_flag:
            return HttpResponseRedirect(reverse('project-detail-zoomed-release', kwargs={
                'slug': project.slug,
                'zoom': '1M',
                'release_flag': release_flag,
            }))
        else:
            return HttpResponseRedirect(reverse('project-detail-zoomed', kwargs={
                'slug': project.slug,
                'zoom': '1M',
            }))

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
        date__lte=today,
    ).order_by('date').values(
        'date',
        'metrics__complexity',
        'metrics__github_issue_age',
        'metrics__github_issues_open',
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

    # Render the HTML and send to client.
    context = {
        'user': request.user,
        'projects': Project.objects.all().order_by('name'),
        'project': project,
        'zoom': zoom,
        'frequency': frequency,
        'show_releases': release_flag != 'no-releases',
        'metrics': metrics,
        'current_lead_time': round(metrics[-1]['github_issue_age'], 1) if len(metrics) > 0 else 0,
        'current_open_tickets': int(metrics[-1]['github_issues_open']) if len(metrics) > 0 else 0,
        'current_complexity_change': round(project.get_complexity_change(), 1),
        'releases': releases,
        'data_tree': json.dumps(project.source_tree_metrics['tree']),
        'min_complexity': project.source_tree_metrics['min_complexity'],
        'max_complexity': project.source_tree_metrics['max_complexity'],
        'min_changes': project.source_tree_metrics['min_changes'],
        'max_changes': project.source_tree_metrics['max_changes'],
    }

    # Usage statistics
    utcnow = datetime.datetime.utcnow()
    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project=project,
        timestamp=utcnow,
        action='project.load',
    )
    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project=project,
        timestamp=utcnow,
        action='project.evolution.zoom_%s' % zoom.lower(),
    )
    if release_flag == 'no-releases':
        Usage.objects.create(
            user=request.user if request.user.is_authenticated else None,
            project=project,
            timestamp=utcnow,
            action='project.evolution.releases.hide',
        )
    else:
        Usage.objects.create(
            user=request.user if request.user.is_authenticated else None,
            project=project,
            timestamp=utcnow,
            action='project.evolution.releases.show',
        )

    html = render_to_string('project/detail.html', context=context, request=request)
    return HttpResponse(html)


@only_matching_authenticated_users
def user_settings(request, username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        raise Http404('User does not exist')

    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project=None,
        timestamp=datetime.datetime.utcnow(),
        action='user_settings.view',
    )

    context = {
        'user': user,
        'projects': user.projects.all().order_by('name'),
    }
    html = render_to_string('settings/user.html', context=context)
    return HttpResponse(html)


@only_matching_authenticated_users
@add_user_and_project
def project_settings(request, username, project_slug, user, project):
    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project=None,
        timestamp=datetime.datetime.utcnow(),
        action='project_settings.view',
    )

    context = {
        'user': request.user,
        'project': project,
    }
    html = render_to_string('settings/project.html', context=context)
    return HttpResponse(html)


@only_matching_authenticated_users
@add_user_and_project
def project_toggle(request, username, project_slug, user, project):
    project.active = not project.active
    project.save()

    utcnow = datetime.datetime.utcnow()

    if project.active:
        Usage.objects.create(
            user=request.user if request.user.is_authenticated else None,
            project=None,
            timestamp=utcnow,
            action='project.activate',
        )
        project.import_data()
    else:
        Usage.objects.create(
            user=request.user if request.user.is_authenticated else None,
            project=None,
            timestamp=utcnow,
            action='project.deactivate',
        )
        project.last_update = None
        project.save()

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


def count_usage(request):
    payload = json.loads(request.body)

    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project_id=payload['project_id'],
        timestamp=parse_datetime(payload['timestamp']),
        action=payload['action'],
    )

    return HttpResponse('')


def project_file_stats(request, slug):
    try:
        project = Project.objects.get(slug=slug)
    except Project.DoesNotExist:
        raise Http404('Project does not exist')

    if project.private:
        if project.user != request.user:
            raise Http404('Project does not exist')

    path = request.GET.get('path')
    days = request.GET.get('days', 30)

    if not path:
        return JsonResponse({})

    # Number of commits in the last n days
    commit_count = project.get_file_commit_count(path, days)
    commit_counts = []
    commit_counts_labels = []

    for author in sorted(commit_count, key=commit_count.get, reverse=True):
        commit_counts_labels.append(author)
        commit_counts.append(commit_count[author])

    # Code ownership of the file
    ownership = project.get_file_ownership(path)

    json = {
        'path': path,
        'link': f'{project.github_repo_url}/blame/master/{path}',

        'complexity_trend': project.get_file_complexity_trend(path, days),
        'complexity_trend_labels': [x for x in range(1, 31)],

        'changes_trend': project.get_file_changes_trend(path, days),
        'changes_trend_labels': [x for x in range(1, 31)],

        'commit_counts': commit_counts,
        'commit_counts_labels': commit_counts_labels,

        'code_ownership': [o['lines'] for o in ownership],
        'code_ownership_labels': [o['author'].split('<')[0].strip() for o in ownership],
    }

    return JsonResponse(json)
