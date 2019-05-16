
from datetime import timedelta
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from maintainer.main import tasks
from maintainer.main.models import Metric, Project
from maintainer.main.utils import resample


def index(request):
    slug = request.GET.get('project', None)
    if not slug:
        project = Project.objects.all().order_by('name').first()
    else:
        project = Project.objects.get(slug=slug)

    metrics = Metric.objects.filter(
        project=project
    ).order_by('date').values(
        'date',
        'metrics__loc',
        'metrics__complexity',
        'metrics__sentry_errors',
        'metrics__gitlab_bug_issues',
        'metrics__number_of_commits',
        'metrics__complexity_per_author',
        'metrics__dependencies_direct',
        'metrics__dependencies_indirect',
        'metrics__dependencies_max',
    )

    today = timezone.now().date()

    current_value = metrics.last()['metrics__complexity']
    try:
        value1 = metrics.filter(
            date__lte=today-timedelta(days=12*30),
            metrics__complexity__isnull=False,
        ).order_by('date').last()['metrics__complexity']
        change1 = 100/current_value*value1-100
    except TypeError:
        change1 = '?'

    try:
        value2 = metrics.filter(
            date__lte=today-timedelta(days=6*30),
            metrics__complexity__isnull=False,
        ).order_by('date').last()['metrics__complexity']
        change2 = 100/current_value*value2-100
    except TypeError:
        change2 = '?'

    try:
        value3 = metrics.filter(
            date__lte=today-timedelta(days=1*30),
            metrics__complexity__isnull=False,
        ).order_by('date').last()['metrics__complexity']
        change3 = 100/current_value*value3-100
    except TypeError:
        change3 = '?'

    metric_stats = [{
        'label': 'Complexity: ',
        'value1': '{:+.0%}'.format(change1) if type(change1) == float else change1,
        'value2': '{:+.0%}'.format(change2) if type(change2) == float else change2,
        'value3': '{:+.0%}'.format(change3) if type(change3) == float else change3,
    },{
        'label': 'GitHub Bug Issues: ',
        'value1': '?',
        'value2': '?',
        'value3': '?',
    }]

    context = {
        'projects': Project.objects.all().order_by('name'),
        'project': project,
        'metrics': resample(metrics, 'M'),
        'metric_stats': metric_stats,
    }

    rendered = render_to_string('index.html', context=context)
    return HttpResponse(rendered)


def update(request):
    for project in Project.objects.all().exclude(slug='flask').order_by('id'):
        imports_to_run = [
            tasks.import_git_metrics.s(),
        ]

        #if 'gitlab' in project.external_services:
        #    imports_to_run.append(
        #        tasks.import_gitlab_issues.s()
        #    )

        #if 'sentry' in project.external_services:
        #    imports_to_run.append(
        #        tasks.import_sentry_errors.s()
        #    )

        tasks.init_project.apply_async(
            args=(project.pk, ),
            link=imports_to_run,
        )

    return HttpResponse('Update started!')
