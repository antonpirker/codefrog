from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework import viewsets

from api_internal.serializers import MetricSerializer, ProjectSerializer
from core.models import Metric, Project


class MetricViewSet(viewsets.ModelViewSet):
    serializer_class = MetricSerializer
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

        metrics = Metric.objects.filter(
            project=project,
        )

        return metrics


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        projects = Project.objects.filter(user=user, active=True)
        return projects
