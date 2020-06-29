import datetime
import json

import structlog
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.decorators import add_user_and_project, only_matching_authenticated_users
from core.models import Metric, Project, Release
from core.utils import resample_metrics, resample_releases
from web.models import Usage
from web.views import landing

logger = structlog.get_logger(__name__)

MONTH = 30
YEAR = 365

def index(request):
    # users that are not logged in see the landing page.
    if not request.user.is_authenticated:
        return landing(request)

    if request.user.is_superuser:
        projects = Project.objects.all().order_by('-active', 'name')
    else:
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
        timestamp=timezone.now(),
        action='repository_list.view',
    )

    html = render_to_string('index.html', context=context, request=request)
    return HttpResponse(html)


def project_detail(request, slug, zoom=None, release_flag=None):
    try:
        project = Project.objects.get(slug=slug)
    except Project.DoesNotExist:
        raise Http404('Project does not exist')

    if project.private \
        and request.user != project.user  \
        and not request.user.is_superuser:
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
        'data_tree': project.current_source_status.tree if project.current_source_status else {},
        'min_complexity': project.current_source_status.min_complexity if project.current_source_status else 1,
        'max_complexity': project.current_source_status.min_complexity if project.current_source_status else 1,
        'min_changes': project.current_source_status.min_changes if project.current_source_status else 1,
        'max_changes': project.current_source_status.max_changes if project.current_source_status else 1,
        'file_churn': project.get_file_churn(),
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
    now = timezone.now()
    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project=project,
        timestamp=now,
        action='project.load',
    )
    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project=project,
        timestamp=now,
        action='project.evolution.zoom_%s' % zoom.lower(),
    )
    if release_flag == 'no-releases':
        Usage.objects.create(
            user=request.user if request.user.is_authenticated else None,
            project=project,
            timestamp=now,
            action='project.evolution.releases.hide',
        )
    else:
        Usage.objects.create(
            user=request.user if request.user.is_authenticated else None,
            project=project,
            timestamp=now,
            action='project.evolution.releases.show',
        )

    html = render_to_string('project/detail.html', context=context, request=request)
    return HttpResponse(html)


@only_matching_authenticated_users
@add_user_and_project
def project_toggle(request, username, project_slug, user, project):
    project.active = not project.active
    project.save()

    project.user.profile.newly_registered = False
    project.user.profile.save()

    now = timezone.now()

    if project.active:
        Usage.objects.create(
            user=request.user if request.user.is_authenticated else None,
            project=None,
            timestamp=now,
            action='project.activate',
        )
        project.ingest()
    else:
        Usage.objects.create(
            user=request.user if request.user.is_authenticated else None,
            project=None,
            timestamp=now,
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

    if project.private \
        and request.user != project.user  \
        and not request.user.is_superuser:
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
