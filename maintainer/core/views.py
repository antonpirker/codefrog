import datetime

from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone

from core.models import Metric, Project, Release
from core.utils import resample


def index(request):
    context = {
        'projects': Project.objects.all().order_by('name'),
    }

    rendered = render_to_string('index.html', context=context)
    return HttpResponse(rendered)


def project_detail(request, slug):
    try:
        project = Project.objects.get(slug=slug)
    except Project.DoesNotExist:
        raise Http404('Project does not exist')

    today = timezone.now()
    begin = today - datetime.timedelta(days=30*3)

    metrics = Metric.objects.filter(
        project=project,
        date__gte=begin,
    ).order_by('date').values(
        'date',
        'metrics__complexity',
        'metrics__github_bug_issues_now_open',
        'metrics__github_bug_issues_avg_days_open',
    )

    releases = Release.objects.filter(
        project=project,
        timestamp__gte=begin,
    )

    context = {
        'projects': Project.objects.all().order_by('name'),
        'project': project,
        'metrics': resample(metrics, 'D'),
        'releases': releases,
    }

    rendered = render_to_string('project/detail.html', context=context)
    return HttpResponse(rendered)
