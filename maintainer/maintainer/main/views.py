from django.http import HttpResponse
from django.template.loader import render_to_string
from maintainer.main import tasks
from maintainer.main.models import Metric, Project
from maintainer.main.utils import resample


def index(request):
    project = Project.objects.all().order_by('name').first()

    metrics = Metric.objects.filter(
        project=project
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
    project = Project.objects.filter(slug='donut-backend').order_by('name').last()

    imports_to_run = [
        tasks.import_git_metrics.s(),
    ]

    import ipdb; ipdb.set_trace()
    if 'gitlab' in project.external_services:
        imports_to_run.append(
            tasks.import_gitlab_issues.s()
        )


    if 'gitlab' in project.external_services:
        imports_to_run.append(
            tasks.import_sentry_errors.s()
        )

    tasks.init_project.apply_async(
        args=(project.pk, ),
        link=imports_to_run,
    )

    return HttpResponse('Update started!')
