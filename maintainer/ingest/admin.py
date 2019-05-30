from django.contrib import admin

from core.models import Metric, Release
from ingest.models import RawIssue, RawCodeChange


@admin.register(RawIssue)
class RawIssueAdmin(admin.ModelAdmin):
    list_display = (
        'project', 'issue_refid', 'opened_at', 'closed_at', 'labels',
    )
    list_filter = (
        'project', 'opened_at',
    )
    ordering = ['project', '-opened_at']


@admin.register(RawCodeChange)
class RawCodeChangeAdmin(admin.ModelAdmin):
    list_display = (
        'project', 'file_path', 'author',
        'complexity_added', 'complexity_removed', 'timestamp',
    )
    list_filter = (
        'project', 'timestamp',
    )
    ordering = ['project', '-timestamp']

