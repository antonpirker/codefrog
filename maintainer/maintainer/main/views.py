from django.http import HttpResponse
from django.template.loader import render_to_string
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
        'metrics__complexity',
        'metrics__sentry_errors',
        'metrics__gitlab_bug_issues',
        'metrics__number_of_authors',
        'metrics__number_of_commits',
        'metrics__complexity_per_author',
    )

    context = {
        'projects': Project.objects.all().order_by('name'),
        'project': project,
        'metrics': [], #resample(metrics, 'M'),
    }

    rendered = render_to_string('index.html', context=context)
    return HttpResponse(rendered)


def update(request):
    for project in Project.objects.filter(pk__lt=4).order_by('name'):
        imports_to_run = [
            tasks.import_git_metrics.s(),
        ]

    #    if 'gitlab' in project.external_services:
    #        imports_to_run.append(
    #            tasks.import_gitlab_issues.s()
    #        )


    #    if 'gitlab' in project.external_services:
    #        imports_to_run.append(
    #            tasks.import_sentry_errors.s()
    #        )

        tasks.init_project.apply_async(
            args=(project.pk, ),
            link=imports_to_run,
        )

    return HttpResponse('Update started!')
