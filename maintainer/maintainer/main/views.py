
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

    today = timezone.now().date()
    last_year = today - timedelta(days=365)

    metrics = Metric.objects.filter(
        project=project,
#        date__gte=last_year,
    ).order_by('date').values(
        'date',
        'metrics__loc',
        'metrics__complexity',
        'metrics__sentry_errors',
        'metrics__gitlab_bug_issues',
        'metrics__github_bug_issues_opened',
        'metrics__github_bug_issues_now_open',
        'metrics__number_of_commits',
        'metrics__complexity_per_author',
        'metrics__dependencies_direct',
        'metrics__dependencies_indirect',
        'metrics__dependencies_max',
    )

    # Changes in Complexity
    current_value =  metrics.filter(metrics__complexity__isnull=False)\
        .last()['metrics__complexity'] or 1

    try:
        value1 = metrics.filter(
            date__lte=today-timedelta(days=1*30),
            metrics__complexity__isnull=False,
        ).order_by('date').last()['metrics__complexity']
    except TypeError:
        value1 = 1
    change1 = (100/(value1 or 1)*current_value-100)/100

    try:
        value2 = metrics.filter(
            date__lte=today-timedelta(days=6*30),
            metrics__complexity__isnull=False,
        ).order_by('date').last()['metrics__complexity']
    except TypeError:
        value2 = 1
    change2 = (100/(value2 or 1)*current_value-100)/100

    try:
        value3 = metrics.filter(
            date__lte=today-timedelta(days=12*30),
            metrics__complexity__isnull=False,
        ).order_by('date').last()['metrics__complexity']
    except TypeError:
        value3 = 1
    change3 = (100/(value3 or 1)*current_value-100)/100

    # Changes in Github Bug Issues Count
    current_value = metrics.filter(metrics__github_bug_issues_now_open__isnull=False)\
        .last()['metrics__github_bug_issues_now_open'] or 1

    try:
        value1_1 = metrics.filter(
            date__lte=today-timedelta(days=1*30),
            metrics__github_bug_issues_now_open__isnull=False,
        ).order_by('date').last()['metrics__github_bug_issues_now_open']
    except TypeError:
        value1_1 = 1
    change1_1 = (100 / (value1_1 or 1) * current_value - 100) / 100

    try:
        value1_2 = metrics.filter(
            date__lte=today-timedelta(days=6*30),
            metrics__github_bug_issues_now_open__isnull=False,
        ).order_by('date').last()['metrics__github_bug_issues_now_open']
    except TypeError:
        value1_2 = 1
    change1_2 = (100/(value1_2 or 1)*current_value-100)/100

    try:
        value1_3 = metrics.filter(
            date__lte=today-timedelta(days=12*30),
            metrics__github_bug_issues_now_open__isnull=False,
        ).order_by('date').last()['metrics__github_bug_issues_now_open']
    except TypeError:
        value1_3 = 1
    change1_3 = (100/(value1_3 or 1)*current_value-100)/100

    metric_stats = [{
        'label': 'Complexity: ',
        'value1': '{:+.0%}'.format(change1) if type(change1) == float else change1,
        'value2': '{:+.0%}'.format(change2) if type(change2) == float else change2,
        'value3': '{:+.0%}'.format(change3) if type(change3) == float else change3,
    }, {
        'label': 'GitHub Bug Issues: ',
        'value1': '{:+.0%}'.format(change1_1) if type(change1_1) == float else change1_1,
        'value2': '{:+.0%}'.format(change1_2) if type(change1_2) == float else change1_2,
        'value3': '{:+.0%}'.format(change1_3) if type(change1_3) == float else change1_3,
    }]

    context = {
        'projects': Project.objects.all().order_by('name'),
        'project': project,
        'metrics': resample(metrics, 'D'),
        'metric_stats': metric_stats,
    }

    rendered = render_to_string('index.html', context=context)
    return HttpResponse(rendered)


def update(request):
    for project in Project.objects.all().order_by('id'):
        imports_to_run = [
            tasks.import_git_metrics.s(),
        ]

        if 'github' in project.external_services:
            imports_to_run.append(
                tasks.import_github_issues.s(),
            )

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
