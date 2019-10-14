from django.contrib import admin

from ingest.models import OpenIssue, RawCodeChange, RawIssue


@admin.register(RawIssue)
class RawIssueAdmin(admin.ModelAdmin):
    list_display = (
        'project', 'issue_refid', 'opened_at', 'closed_at', 'labels',
    )
    list_filter = (
        'project', 'opened_at',
    )
    ordering = ['project', '-opened_at']


@admin.register(OpenIssue)
class OpenIssueAdmin(admin.ModelAdmin):
    list_display = (
        'project', 'issue_refid', 'query_time', 'labels',
    )
    list_filter = (
        'project',
    )
    ordering = ['project', '-query_time']


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

