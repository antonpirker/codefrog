from django.contrib import admin

from maintainer.main.models import CodeMetric, ExternalMetric


class CodeMetricAdmin(admin.ModelAdmin):
    list_display = (
        'project_slug', 'date', 'git_reference',
        'complexity', 'loc',
    )
    ordering = ['project_slug', '-date', ]

admin.site.register(CodeMetric, CodeMetricAdmin)


class ExternalMetricAdmin(admin.ModelAdmin):
    list_display = (
        'project_slug', 'date',
        'jira_bug_issues', 'gitlab_bug_issues', 'sentry_errors',
    )
    ordering = ['project_slug', '-date', ]

admin.site.register(ExternalMetric, ExternalMetricAdmin)
