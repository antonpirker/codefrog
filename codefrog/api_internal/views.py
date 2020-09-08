import datetime

from dateutil.parser import parse
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions
from rest_framework import viewsets

from api_internal.serializers import SimpleMetricSerializer, ProjectSerializer, ReleaseSerializer, \
    FileChangesSerializer, SourceStatusSerializer
from api_internal.utils import get_best_frequency
from core.models import Metric, Project, Release
from core.utils import resample_metrics, resample_releases


class MetricViewSet(viewsets.ModelViewSet):
    serializer_class = SimpleMetricSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project_pk = self.kwargs['project_pk']
        user = self.request.user
        project = get_object_or_404(
            Project,
            pk=project_pk,
            user=user,
            active=True,
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
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project_pk = self.kwargs['project_pk']
        user = self.request.user
        project = get_object_or_404(
            Project,
            pk=project_pk,
            user=user,
            active=True,
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
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project_pk = self.kwargs['project_pk']
        user = self.request.user
        project = get_object_or_404(
            Project,
            pk=project_pk,
            user=user,
            active=True,
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
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        project_pk = self.kwargs['project_pk']
        user = self.request.user
        project = get_object_or_404(
            Project,
            pk=project_pk,
            user=user,
            active=True,
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

        import ipdb; ipdb.set_trace()
        return [source_status, ]


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        projects = Project.objects.filter(user=user, active=True)
        return projects
