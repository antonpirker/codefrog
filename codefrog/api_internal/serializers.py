
from rest_framework import serializers

from core.models import Metric, Project


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            'id',
            'name', 'slug', 'private', 'active', 'status', 'last_update',
            'user',
        ]
        depth = 1


class MetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = Metric
        fields = ['date', 'file_path', 'metrics']
