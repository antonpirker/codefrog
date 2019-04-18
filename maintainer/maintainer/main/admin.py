from django.contrib import admin

from maintainer.main.models import Metric


class MetricAdmin(admin.ModelAdmin):
    list_display = (
        'project_slug', 'git_reference', 'date', 'metric',
    )
    ordering = ['project_slug', '-date', ]

admin.site.register(Metric, MetricAdmin)
