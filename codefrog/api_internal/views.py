import datetime

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions
from rest_framework import viewsets

from api_internal.serializers import SimpleMetricSerializer, MetricSerializer, ProjectSerializer
from core.models import Metric, Project
from core.utils import resample_metrics, resample_releases


# TODO: calculate frequency from date_from and date_to
# TODO: private projects can only be requested by owner
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

        # because we will resample the queryset (
        # and then we return something that is not a queryset)
        # we need to filter by hand.
        kwargs = {
            'project': project,
        }
        date_from = self.request.GET.get('date_from', None)
        if date_from:
            kwargs['date__gte'] = date_from

        date_to = self.request.GET.get('date_to', None)
        if date_to:
            kwargs['date__lte'] = date_to

        # Calculate the best frequency for the given time span
        frequency = 'D' #TODO: make dynamic

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

        metrics = resample_metrics(metrics, frequency)

        return metrics

# TODO: create ReleaseViewSet similar to MetricViewSet (but for releases)

# TODO: create similar viewset for file churn. see: get_file_churn()

# TODO: create similar viewset for state of affairs

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        projects = Project.objects.filter(user=user, active=True)
        return projects
