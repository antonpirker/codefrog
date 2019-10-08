import datetime
import json
import os
import secrets

from django.conf import settings
from django.contrib.auth.models import User
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils import timezone

from core.models import Metric, Project, Release
from core.utils import only_matching_authenticated_users, resample_metrics, \
    resample_releases, add_user_and_project, run_shell_command
from ingest.models import RawCodeChange

MONTH = 30
YEAR = 365

EXCLUDE = [
    '/.git/',
]


def index(request):
    if request.user.is_authenticated:
        projects = request.user.projects.all().order_by('-active', 'name')
    else:
        projects = Project.objects.none()

    context = {
        'user': request.user,
        'projects': projects,
        'github_app_client_id': settings.GITHUB_APP_CLIENT_ID,
        'github_redirect_uri': settings.GITHUB_AUTH_REDIRECT_URI,
        'github_state': secrets.token_urlsafe(50),
    }

    if request.user.is_authenticated:
        html = render_to_string('index.html', context=context)
    else:
        html = render_to_string('landing.html', context=context)

    return HttpResponse(html)


def project_detail(request, slug, zoom=None, release_flag=None):
    try:
        project = Project.objects.get(slug=slug)
    except Project.DoesNotExist:
        raise Http404('Project does not exist')

    if project.private:
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
        'metrics__github_bug_issues_open',
        'metrics__github_other_issues_open',
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

    def get_file_ownership(filename, project):
        cmd = f'git shortlog -s -n -e -- {filename}'
        output = run_shell_command(cmd, cwd=project.repo_dir)
        output = [line for line in output.split('\n') if line]

        ownerships = []

        for line in output:
            lines, author = line.lstrip().split('\t')
            ownerships.append({
                'author': author,
                'lines:': int(lines),
            })

        return ownerships

    min_complexity = 0
    max_complexity = 0
    min_changes = 0
    max_changes = 0

    for root_dir, dirs, files in os.walk(project.repo_dir):
        for f in files:
            full_path = os.path.join(root_dir, f)
            if any(x in full_path for x in EXCLUDE):  # exclude certain directories
                continue
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
                    COMPLEXITY_THRESSHOLD = 2000

                    complexity = get_file_complexity(full_path)
                    if complexity < min_complexity:
                        min_complexity = complexity
                    if complexity > max_complexity:
                        max_complexity = complexity

                    if complexity < COMPLEXITY_THRESSHOLD:
                        changes = get_file_changes(full_path, project)
                        if changes < min_changes:
                            min_changes = changes
                        if changes > max_changes:
                            max_changes = changes

                        repo_link = '{}blame/master{}'.format(
                            project.github_repo_url,
                            full_path.replace(project.repo_dir, ''),
                        ).replace('//', '/')

                        ownership = get_file_ownership(full_path, project)

                        child_node = {
                            'name': node_name,
                            'size': complexity,
                            'changes': changes,
                            'ownership': ownership,
                            'repo_link': repo_link,
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

    html = render_to_string('project/detail.html', context=context)
    return HttpResponse(html)


@only_matching_authenticated_users
def user_settings(request, username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        raise Http404('User does not exist')

    context = {
        'user': user,
        'projects': user.projects.all().order_by('name'),
    }
    html = render_to_string('settings/user.html', context=context)
    return HttpResponse(html)


@only_matching_authenticated_users
@add_user_and_project
def project_settings(request, username, project_slug, user, project):
    context = {
        'project': project,
    }
    html = render_to_string('settings/project.html', context=context)
    return HttpResponse(html)


@only_matching_authenticated_users
@add_user_and_project
def project_toggle(request, username, project_slug, user, project):
    project.active = not project.active
    project.save()

    if project.active:
        project.import_data()

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
