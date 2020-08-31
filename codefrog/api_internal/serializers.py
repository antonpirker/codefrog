
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


class SimpleMetricSerializer(serializers.Serializer):
    date = serializers.DateTimeField()
    complexity = serializers.FloatField()
    github_issue_age = serializers.FloatField()
    github_issues_open = serializers.FloatField()
    github_issues_closed = serializers.FloatField()
    github_pull_requests_merged = serializers.FloatField()
    github_pull_requests_cumulative_age = serializers.FloatField()
    github_avg_pull_request_age = serializers.SerializerMethodField()

    def get_github_avg_pull_request_age(self, obj):
        avg_age = obj['github_pull_requests_cumulative_age'] / obj['github_pull_requests_merged'] \
            if obj['github_pull_requests_merged'] != 0 else 0
        avg_age = avg_age / 60 / 60

        return avg_age


class MetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = Metric
        fields = ['date', 'file_path', 'metrics']
