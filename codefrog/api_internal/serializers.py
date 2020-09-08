import datetime

from dateutil.parser import parse
from django.utils import timezone
from rest_framework import serializers

from core.models import Metric, Project


class ProjectSerializer(serializers.ModelSerializer):
    state_of_affairs = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id',
            'name', 'slug', 'private', 'active', 'status', 'last_update',
            'user', 'state_of_affairs',
        ]

    def get_state_of_affairs(self, obj):
        date_to = timezone.now()
        date_from = date_to - datetime.timedelta(days=14)

        date_override = self.context.get("request").GET.get('date_from', None)
        if date_override:
            date_from = parse(date_override)

        date_override = self.context.get("request").GET.get('date_to', None)
        if date_override:
            date_to = parse(date_override)

        return obj.get_state_of_affairs(date_from, date_to);

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


class ReleaseSerializer(serializers.Serializer):
    date = serializers.DateTimeField(source='timestamp')
    name = serializers.CharField()


class FileChangesSerializer(serializers.Serializer):
    file_path = serializers.CharField()
    changes = serializers.FloatField()
    repo_link = serializers.CharField()


class SourceStatusSerializer(serializers.Serializer):
    tree = serializers.DictField()
    min_changes = serializers.IntegerField()
    max_changes = serializers.IntegerField()
