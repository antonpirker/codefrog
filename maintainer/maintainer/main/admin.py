from django.contrib import admin

from maintainer.main.models import Metric


class MetricAdmin(admin.ModelAdmin):
    list_display = (
        'project_slug', 'date', 'git_reference',
        'complexity', 'loc',
        'jira_bug_issues', 'gitlab_bug_issues', 'sentry_errors',
    )
    ordering = ['project_slug', '-date', ]

admin.site.register(Metric, MetricAdmin)

