import datetime
import os

from dateutil.parser import parse
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions
from rest_framework import viewsets

from api_internal.serializers import SimpleMetricSerializer, ProjectSerializer, ReleaseSerializer, \
    FileChangesSerializer, SourceStatusSerializer, FileStatusSerializer
from api_internal.utils import get_best_frequency
from core.models import Metric, Project, Release, SourceNode
from core.utils import resample_metrics, resample_releases


class MetricViewSet(viewsets.ModelViewSet):
    serializer_class = SimpleMetricSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        project_pk = self.kwargs['project_pk']
        user = self.request.user
        kwargs = {
            'active': True,
            'pk': project_pk,
        }
        if user.is_authenticated:
            kwargs['user'] = user
        else:
            kwargs['private'] = False

        # Superusers can see projects from other users
        if user.is_superuser:
            del kwargs['user']

        project = get_object_or_404(
            Project,
            **kwargs,
        )

        # Private projects can only be requested by owner or superuser
        if project.private \
                and project.user != user \
                and not user.is_superuser:
            raise Http404('Project does not exist')

        # because we will resample the queryset (
        # and then we return something that is not a queryset)
        # we need to filter by hand.
        kwargs = {
            'project': project,
        }
        try:
            kwargs['date__gte'] = parse(self.request.GET.get('date_from'))
        except (TypeError, ValueError):
            pass

        try:
            kwargs['date__lte'] = parse(self.request.GET.get('date_to'))
        except (TypeError, ValueError):
            pass

        # Get metrics in the desired frequency
        metrics = Metric.objects.filter(**kwargs).order_by('date').values(
            'date',
            'metrics__complexity',
            'metrics__github_issue_age',
            'metrics__github_issues_open',
            'metrics__github_issues_closed',
            'metrics__github_pull_requests_merged',
            'metrics__github_pull_requests_cumulative_age',
        )
        if len(metrics) > 0:
            frequency = get_best_frequency(metrics[0]['date'], metrics[len(metrics)-1]['date'])
            metrics = resample_metrics(metrics, frequency)

        return metrics


class ReleaseViewSet(viewsets.ModelViewSet):
    serializer_class = ReleaseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        project_pk = self.kwargs['project_pk']
        user = self.request.user
        kwargs = {
            'active': True,
            'pk': project_pk,
        }
        if user.is_authenticated:
            kwargs['user'] = user
        else:
            kwargs['private'] = False

        # Superusers can see projects from other users
        if user.is_superuser:
            del kwargs['user']

        project = get_object_or_404(
            Project,
            **kwargs,
        )

        # Private projects can only be requested by owner or superuser
        if project.private \
                and project.user != user \
                and not user.is_superuser:
            raise Http404('Project does not exist')

        # because we will resample the queryset (
        # and then we return something that is not a queryset)
        # we need to filter by hand.
        kwargs = {
            'project': project,
        }
        try:
            kwargs['timestamp__date__gte'] = parse(self.request.GET.get('date_from'))
        except (TypeError, ValueError):
            pass

        try:
            kwargs['timestamp__date__lte'] = parse(self.request.GET.get('date_to'))
        except (TypeError, ValueError):
            pass

        releases = Release.objects.filter(**kwargs).order_by('timestamp').values(
            'timestamp',
            'name',
        )

        if len(releases) > 0:
            frequency = get_best_frequency(releases[0]['timestamp'], releases[len(releases) - 1]['timestamp'])
            releases = resample_releases(releases, frequency)

        return releases

class FileChangesViewSet(viewsets.ModelViewSet):
    serializer_class = FileChangesSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        project_pk = self.kwargs['project_pk']
        user = self.request.user
        kwargs = {
            'active': True,
            'pk': project_pk,
        }
        if user.is_authenticated:
            kwargs['user'] = user
        else:
            kwargs['private'] = False

        # Superusers can see projects from other users
        if user.is_superuser:
            del kwargs['user']

        project = get_object_or_404(
            Project,
            **kwargs,
        )

        # Private projects can only be requested by owner or superuser
        if project.private \
                and project.user != user \
                and not user.is_superuser:
            raise Http404('Project does not exist')

        try:
            date_from = parse(self.request.GET.get('date_from'))
        except (TypeError, ValueError):
            date_from = datetime.date(1970, 1, 1)

        try:
            date_to = parse(self.request.GET.get('date_to'))
        except (TypeError, ValueError):
            date_to = timezone.now().date()

        changes = project.get_file_changes(date_from, date_to)
        return changes


class SourceStatusViewSet(viewsets.ModelViewSet):
    serializer_class = SourceStatusSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        project_pk = self.kwargs['project_pk']
        user = self.request.user
        kwargs = {
            'active': True,
            'pk': project_pk,
        }
        if user.is_authenticated:
            kwargs['user'] = user
        else:
            kwargs['private'] = False

        # Superusers can see projects from other users
        if user.is_superuser:
            del kwargs['user']

        project = get_object_or_404(
            Project,
            **kwargs,
        )

        # Private projects can only be requested by owner or superuser
        if project.private \
                and project.user != user \
                and not user.is_superuser:
            raise Http404('Project does not exist')

        try:
            date_to = parse(self.request.GET.get('date_to'))
        except (TypeError, ValueError):
            date_to = timezone.now().date()

        source_status = project.get_source_status(date=date_to)
        if not source_status:
            return []

        return [source_status, ]


class FileStatusViewSet(viewsets.ModelViewSet):
    serializer_class = FileStatusSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        project_pk = self.kwargs['project_pk']
        user = self.request.user
        kwargs = {
            'active': True,
            'pk': project_pk,
        }
        if user.is_authenticated:
            kwargs['user'] = user
        else:
            kwargs['private'] = False

        # Superusers can see projects from other users
        if user.is_superuser:
            del kwargs['user']

        project = get_object_or_404(
            Project,
            **kwargs
        )

        # Private projects can only be requested by owner or superuser
        if project.private \
                and project.user != user \
                and not user.is_superuser:
            raise Http404('Project does not exist')

        try:
            date_from = parse(self.request.GET.get('date_from'))
        except (TypeError, ValueError):
            date_from = datetime.date(1970, 1, 1)

        try:
            date_to = parse(self.request.GET.get('date_to'))
        except (TypeError, ValueError):
            date_to = timezone.now().date()

        path = self.request.GET.get('path')
        if not path:
            return []

        is_file = SourceNode.objects.get(
            source_status=project.current_source_status,
            path=os.path.join(project.github_repo_name, path),
        ).children.all().count() == 0

        if is_file:
            data_for_path = SourceNode.objects.filter(
                source_status=project.current_source_status,
                path=os.path.join(project.github_repo_name, path),
            ).exists()
            if not data_for_path:
                return []

            # Number of commits in the given time period
            code_changes = project.codechange_set.filter(
                timestamp__date__gte=date_from,
                timestamp__date__lte=date_to,
                file_path=path,
            )\
            .values('author')\
            .annotate(count=Count('author'))\
            .order_by('-count', 'author')

        else:
            data_for_path = SourceNode.objects.filter(
                source_status=project.current_source_status,
                path__startswith=os.path.join(project.github_repo_name, path),
            ).exists()
            if not data_for_path:
                return []

            # Number of commits in the given time period
            code_changes = project.codechange_set.filter(
                timestamp__date__gte=date_from,
                timestamp__date__lte=date_to,
                file_path__startswith=path,
            ) \
            .values('author') \
            .annotate(count=Count('author')) \
            .order_by('-count', 'author')

        commit_counts = [x['count'] for x in code_changes]
        commit_counts_labels = [x['author'].split(' <')[0] for x in code_changes]

#        import ipdb; ipdb.set_trace()

        # Code ownership of the file
        ownership = project.get_file_ownership(path)

        complexity_trend = project.get_file_complexity_trend(path, date_from, date_to)
        complexity_trend_labels = [x[0] for x in complexity_trend]
        complexity_trend = [x[1] for x in complexity_trend]

        changes_trend = project.get_file_changes_trend(path, date_from, date_to)
        changes_trend_labels = [x[0] for x in changes_trend]
        changes_trend = [x[1] for x in changes_trend]

        json = {
            'path': path,
            'link': f'{project.github_repo_url}/blame/master/{path}',

            'code_ownership': [o['lines'] for o in ownership],
            'code_ownership_labels': [o['author'].split('<')[0].strip() for o in ownership],

            'commit_counts': commit_counts,
            'commit_counts_labels': commit_counts_labels,

            'complexity_trend': complexity_trend,
            'complexity_trend_labels': complexity_trend_labels,

            'changes_trend': changes_trend,
            'changes_trend_labels': changes_trend_labels,
        }

        return [json, ]

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        kwargs = {
            'active': True,
        }
        if user.is_authenticated:
            kwargs['user'] = user
        else:
            kwargs['private'] = False

        # Superusers can see projects from other users
        if user.is_superuser:
            del kwargs['user']

        projects = Project.objects.filter(**kwargs)
        return projects
