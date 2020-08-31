from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework import viewsets
from core.utils import resample_metrics, resample_releases

from api_internal.serializers import SimpleMetricSerializer, MetricSerializer, ProjectSerializer
from core.models import Metric, Project



# TODO: add filtering date_from
# TODO: add filtering date_to
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

        frequency = 'D' #TODO: make dynamic

        # Get metrics in the desired frequency
        metrics = Metric.objects.filter(
            project=project,
        ).order_by('date').values(
            'date',
            'metrics__complexity',
            'metrics__github_issue_age',
            'metrics__github_issues_open',
            'metrics__github_issues_closed',
            'metrics__github_pull_requests_merged',
            'metrics__github_pull_requests_cumulative_age',
        )

        if metrics.count() > 0:
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
