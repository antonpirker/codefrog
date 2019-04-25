from django.contrib import admin
from django.contrib.postgres import fields

from django_json_widget.widgets import JSONEditorWidget

from maintainer.main.models import Metric


@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = (
        'project_slug', 'date', 'git_reference',
    )
    ordering = ['project_slug', '-date', ]

    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }
