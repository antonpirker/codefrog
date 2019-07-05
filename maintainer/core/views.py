import datetime
import os
import json

from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone

from core.models import Metric, Project, Release
from core.utils import resample_metrics, resample_releases
from ingest.models import RawCodeChange

MONTH = 30
YEAR = 365


def index(request):
    context = {
        'projects': Project.objects.all().order_by('name'),
    }

    rendered = render_to_string('index.html', context=context)
    return HttpResponse(rendered)


def project_detail(request, slug, zoom=None, release_flag=None):
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
    if metrics.count() > 0:
        metrics = resample_metrics(metrics, frequency)

    releases = Release.objects.filter(
        project=project,
        timestamp__gte=begin,
    ).order_by('timestamp').values(
        'timestamp',
        'name',
    )
    if releases.count() > 0:
        releases = resample_releases(releases, frequency)

    if release_flag == 'no-releases':
        releases = []

    root = {
        'name': 'root',
        'children': [],
    }

    def get_file_complexity(filename):
        complexity = 0
        with open(filename) as file:
            try:
                for line in file:
                    complexity += len(line) - len(line.lstrip())
            except UnicodeDecodeError:
                # TODO: This should only happen for binary files like jpg,
                #  but could be potential a real hard to find bug if the complexity is always wrong.
                pass

        return complexity

    def get_file_changes(filename, project):
        return RawCodeChange.objects.filter(
            project=project,
            file_path=filename.replace('{}{}'.format(project.repo_dir, os.sep), ''),
        ).count()

    min_complexity = 0
    max_complexity = 0
    min_changes = 0
    max_changes = 0

    for root_dir, dirs, files in os.walk(project.repo_dir):
        for f in files:
            full_path = os.path.join(root_dir, f)
            parts = [part for part in full_path.split(os.sep) if part]
            parts = parts[len(project.repo_dir.split(os.sep)) - 2:]
            current_node = root
            for idx, part in enumerate(parts):
                children = current_node['children']
                node_name = part

                if idx + 1 < len(parts):
                    child_node = {
                        'name': node_name,
                        'children': []
                    }

                    found_child = False
                    for child in children:
                        if child['name'] == node_name:
                            child_node = child
                            found_child = True
                            break

                    if not found_child:
                        children.append(child_node)
                    current_node = child_node

                else:
                    COMPLEXITY_THRESSHOLD = 5000

                    complexity = get_file_complexity(full_path)
                    if complexity < min_complexity:
                        min_complexity = complexity
                    if complexity > max_complexity:
                        max_complexity = complexity

                    changes = get_file_changes(full_path, project)
                    if changes < min_changes:
                        min_changes = changes
                    if changes > max_changes:
                        max_changes = changes

                    if complexity < COMPLEXITY_THRESSHOLD:
                        child_node = {
                            'name': node_name,
                            'size': complexity,
                            'changes': changes,
                        }
                        children.append(child_node)

    # Render the HTML and send to client.
    context = {
        'projects': Project.objects.all().order_by('name'),
        'project': project,
        'zoom': zoom,
        'frequency': frequency,
        'show_releases': release_flag != 'no-releases',
        'metrics': metrics,
        'releases': releases,
        'data_tree': json.dumps(root),
        'min_complexity': min_complexity,
        'max_complexity': max_complexity,
        'min_changes': min_changes,
        'max_changes': max_changes,
    }

    rendered = render_to_string('project/detail.html', context=context)
    return HttpResponse(rendered)
