from django.http import Http404, HttpResponse
from django.template.loader import render_to_string

from core.models import Metric, Project
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

    metrics = Metric.objects.filter(
        project=project,
    ).order_by('date').values(
        'date',
        'metrics__complexity',
        'metrics__github_bug_issues_now_open',
        'metrics__github_bug_issues_avg_days_open',
    )

    context = {
        'projects': Project.objects.all().order_by('name'),
        'project': project,
        'metrics': resample(metrics, 'W'),
    }

    rendered = render_to_string('project/detail.html', context=context)
    return HttpResponse(rendered)
