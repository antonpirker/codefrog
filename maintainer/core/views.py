import datetime

from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone

from core.models import Metric, Project, Release
from core.utils import resample


MONTH = 30
YEAR = 365


def index(request):
    context = {
        'projects': Project.objects.all().order_by('name'),
    }

    rendered = render_to_string('index.html', context=context)
    return HttpResponse(rendered)


def project_detail(request, slug, zoom=None):
    try:
        project = Project.objects.get(slug=slug)
    except Project.DoesNotExist:
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

    # Get the data in the desired frequency
    metrics = Metric.objects.filter(
        project=project,
        date__gte=begin,
    ).order_by('date').values(
        'date',
        'metrics__complexity',
        'metrics__github_bug_issues_now_open',
        'metrics__github_bug_issues_avg_days_open',
    )
    metrics = resample(metrics, frequency)

    releases = Release.objects.filter(
        project=project,
        timestamp__gte=begin,
    )

    # Render the HTML and send to client.
    context = {
        'projects': Project.objects.all().order_by('name'),
        'project': project,
        'zoom': zoom,
        'metrics': metrics,
        'releases': releases,
    }

    rendered = render_to_string('project/detail.html', context=context)
    return HttpResponse(rendered)
