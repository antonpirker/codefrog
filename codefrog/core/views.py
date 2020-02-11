import datetime
import json

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
from core.views_website import landing
from incomingwebhooks.github.utils import get_access_token, \
    get_app_installation_repositories

MONTH = 30
YEAR = 365

def index(request):
    # users that are not logged in see the landing page.
    if not request.user.is_authenticated:
        return landing(request)

    """
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
    """
    projects = request.user.projects.all().order_by('-active', 'name')

    context = {
        'user': request.user,
        'projects': projects,
        'github_app_client_id': settings.GITHUB_APP_CLIENT_ID,
        'github_redirect_uri': settings.GITHUB_AUTH_REDIRECT_URI,
    }

    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project_id=None,
        timestamp=datetime.datetime.utcnow(),
        action='repository_list.view',
    )

    html = render_to_string('index.html', context=context, request=request)
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

    source_tree_metrics = project.source_tree_metrics if project.source_tree_metrics else {}
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
        'data_tree': json.dumps(source_tree_metrics['tree'] if 'tree' in source_tree_metrics else {}),
        'min_complexity': source_tree_metrics['min_complexity'] if 'min_complexity' in source_tree_metrics else 0,
        'max_complexity': source_tree_metrics['max_complexity'] if 'max_complexity' in source_tree_metrics else 0,
        'min_changes': source_tree_metrics['min_changes'] if 'min_changes' in source_tree_metrics else 0,
        'max_changes': source_tree_metrics['max_changes'] if 'max_changes' in source_tree_metrics else 0,
    }

    """
    # THIS IS ONLY FOR MAKING NICE SCREENSHOTS!
    from pprint import pprint
    pprint(context)

    from django.utils.dateparse import parse_datetime
    metrics = [{
            'complexity': -37663,
            'date': parse_datetime('2019-12-28 00:00:00'),
            'github_issue_age': 119.79222648752399,
            'github_issues_open': 82
        },
        {
            'complexity': -37663,
            'date': parse_datetime('2019-12-29 00:00:00'),
            'github_issue_age': 119.82637889688249,
            'github_issues_open': 83
        },
        {
            'complexity': -37416,
            'date': parse_datetime('2019-12-30 00:00:00'),
            'github_issue_age': 119.80330618112123,
            'github_issues_open': 86
        },
        {
            'complexity': -37416,
            'date': parse_datetime('2019-12-31 00:00:00'),
            'github_issue_age': 119.80967201340675,
            'github_issues_open': 88
        },
        {
            'complexity': -37415,
            'date': parse_datetime('2020-01-01 00:00:00'),
            'github_issue_age': 119.78784979669935,
            'github_issues_open': 90
        },
        {
            'complexity': -37415,
            'date': parse_datetime('2020-01-02 00:00:00'),
            'github_issue_age': 119.73793597706641,
            'github_issues_open': 93
        },
        {
            'complexity': -37415,
            'date': parse_datetime('2020-01-03 00:00:00'),
            'github_issue_age': 119.77459407831901,
            'github_issues_open': 93
        },
        {
            'complexity': -37142,
            'date': parse_datetime('2020-01-04 00:00:00'),
            'github_issue_age': 119.86843361986628,
            'github_issues_open': 89
        },
        {
            'complexity': -36936,
            'date': parse_datetime('2020-01-05 00:00:00'),
            'github_issue_age': 119.84685114503817,
            'github_issues_open': 88
        },

        {
            'complexity': -36405,
            'date': parse_datetime('2020-01-06 00:00:00'),
            'github_issue_age': 119.84769775678866,
            'github_issues_open': 107
        },
        {
            'complexity': -35551,
            'date': parse_datetime('2020-01-07 00:00:00'),
            'github_issue_age': 119.91548630783758,
            'github_issues_open': 106
        },
        {
            'complexity': -35551,
            'date': parse_datetime('2020-01-08 00:00:00'),
            'github_issue_age': 119.92639773531494,
            'github_issues_open': 108
        },
        {
            'complexity': -35551,
            'date': parse_datetime('2020-01-09 00:00:00'),
            'github_issue_age': 119.96604574392832,
            'github_issues_open': 109
        },
        {
            'complexity': -35379,
            'date': parse_datetime('2020-01-10 00:00:00'),
            'github_issue_age': 120.03418198962754,
            'github_issues_open': 105
        },
        {
            'complexity': -34273,
            'date': parse_datetime('2020-01-11 00:00:00'),
            'github_issue_age': 119.90352941176471,
            'github_issues_open': 108
        },
        {
            'complexity': -34273,
            'date': parse_datetime('2020-01-12 00:00:00'),
            'github_issue_age': 119.88669487541138,
            'github_issues_open': 111
        },
        {
            'complexity': -34273,
            'date': parse_datetime('2020-01-13 00:00:00'),
            'github_issue_age': 119.84245127964311,
            'github_issues_open': 115
        },
        {
            'complexity': -34255,
            'date': parse_datetime('2020-01-14 00:00:00'),
            'github_issue_age': 119.82735163030729,
            'github_issues_open': 115
        },
        {
            'complexity': -34255,
            'date': parse_datetime('2020-01-15 00:00:00'),
            'github_issue_age': 119.86846424384525,
            'github_issues_open': 115
        },
        {
            'complexity': -36936,
            'date': parse_datetime('2020-01-16 00:00:00'),
            'github_issue_age': 119.85363528009535,
            'github_issues_open': 89
        },
        {
            'complexity': -36725,
            'date': parse_datetime('2020-01-17 00:00:00'),
            'github_issue_age': 119.7750535586765,
            'github_issues_open': 93
        },
        {
            'complexity': -36725,
            'date': parse_datetime('2020-01-18 00:00:00'),
            'github_issue_age': 117.78306374881066,
            'github_issues_open': 93
        },
        {
            'complexity': -36725,
            'date': parse_datetime('2020-01-19 00:00:00'),
            'github_issue_age': 117,
            'github_issues_open': 96
        },
        {
            'complexity': -36725,
            'date': parse_datetime('2020-01-20 00:00:00'),
            'github_issue_age': 115.9,
            'github_issues_open': 80
        },
        {
            'complexity': -36725,
            'date': parse_datetime('2020-01-21 00:00:00'),
            'github_issue_age': 112.7,
            'github_issues_open': 76
        },
        {
            'complexity': -36725,
            'date': parse_datetime('2020-01-22 00:00:00'),
            'github_issue_age': 111.6,
            'github_issues_open': 71
        },
        {
            'complexity': -36721,
            'date': parse_datetime('2020-01-23 00:00:00'),
            'github_issue_age': 110.2,
            'github_issues_open': 72
        },
        {
            'complexity': -36618,
            'date': parse_datetime('2020-01-24 00:00:00'),
            'github_issue_age': 108,
            'github_issues_open': 55
        },
        {
            'complexity': -36413,
            'date': parse_datetime('2020-01-25 00:00:00'),
            'github_issue_age': 107.7,
            'github_issues_open': 51
        },
        {
            'complexity': -36413,
            'date': parse_datetime('2020-01-26 00:00:00'),
            'github_issue_age': 104.6,
            'github_issues_open': 47
        },
        {
            'complexity': -36413,
            'date': parse_datetime('2020-01-27 00:00:00'),
            'github_issue_age': 100.5,
            'github_issues_open': 30
        },
    ]
    """
    """
    metrics = [{
            'complexity': -37663,
            'date': parse_datetime('2019-12-28 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -37663,
            'date': parse_datetime('2019-12-29 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -37416,
            'date': parse_datetime('2019-12-30 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -37416,
            'date': parse_datetime('2019-12-31 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -37415,
            'date': parse_datetime('2020-01-01 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -37415,
            'date': parse_datetime('2020-01-02 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -37415,
            'date': parse_datetime('2020-01-03 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -37142,
            'date': parse_datetime('2020-01-04 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -36936,
            'date': parse_datetime('2020-01-05 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },

        {
            'complexity': -36405,
            'date': parse_datetime('2020-01-06 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -35551,
            'date': parse_datetime('2020-01-07 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -35551,
            'date': parse_datetime('2020-01-08 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -35551,
            'date': parse_datetime('2020-01-09 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -35379,
            'date': parse_datetime('2020-01-10 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -34273,
            'date': parse_datetime('2020-01-11 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -34273,
            'date': parse_datetime('2020-01-12 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -34273,
            'date': parse_datetime('2020-01-13 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -34255,
            'date': parse_datetime('2020-01-14 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -34255,
            'date': parse_datetime('2020-01-15 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -36936,
            'date': parse_datetime('2020-01-16 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -36725,
            'date': parse_datetime('2020-01-17 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -36725,
            'date': parse_datetime('2020-01-18 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -36725,
            'date': parse_datetime('2020-01-19 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -36725,
            'date': parse_datetime('2020-01-20 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -36725,
            'date': parse_datetime('2020-01-21 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -36725,
            'date': parse_datetime('2020-01-22 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -36721,
            'date': parse_datetime('2020-01-23 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -36618,
            'date': parse_datetime('2020-01-24 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -36413,
            'date': parse_datetime('2020-01-25 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -36413,
            'date': parse_datetime('2020-01-26 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
        {
            'complexity': -36413,
            'date': parse_datetime('2020-01-27 00:00:00'),
            'github_issue_age': 0,
            'github_issues_open': 0
        },
    ]
    """

    context['metrics'] = metrics

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

    project.user.profile.newly_registered = False
    project.user.profile.save()

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

    """
    # THIS IS ONLY FOR MAKING NICE SCREENSHOTS!

    print('-----------------------------------------------------------------')
    print(json['commit_counts'])
    print('-----------------------------------------------------------------')
    print(json['commit_counts_labels'])
    print('-----------------------------------------------------------------')

    json['path'] = 'internal/converter/pages_capture.go'
    json['complexity_trend'] = [4, 4, 8, 8, 8, 10, 10, 12, 12, 12, 12, 12, 16, 34, 34, 34, 7, 7, 7, 7, 17, 18, 24, 24, 37, 37, 37, 37, 37, 37, ]
    json['changes_trend'] = [4, 4, 12, 4, 4, 4, 10, 8, 10, 4, 4, 4, 4, 4, 10, 4, 4, 4, 10, 10, 12, 4, 10, 4, 4, 4, 4, 12, 13, 15, ]

    json['code_ownership'] = [60, 13, 6, 1, 19]
    json['code_ownership_labels'] = ['Sergey Brin', 'Grace Hopper', '李彦宏', 'Elliot Alderson', '12 Others']

    json['commit_counts'] = [1, 12]
    json['commit_counts_labels'] = ['Sergey Brin', 'Grace Hopper',]
    """

    return JsonResponse(json)