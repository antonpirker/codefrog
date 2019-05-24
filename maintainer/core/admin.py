from django.contrib import admin
from django.contrib.postgres import fields

from django_json_widget.widgets import JSONEditorWidget

from core.models import Project, Metric


class ModelAdminWithJSONWidget(admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }


@admin.register(Project)
class ProjectAdmin(ModelAdminWithJSONWidget):
    list_display = (
        'id', 'name', 'slug', 'git_url',
    )
    ordering = ['name', ]

    prepopulated_fields = {'slug': ('name',)}


@admin.register(Metric)
class MetricAdmin(ModelAdminWithJSONWidget):
    list_display = (
        'project', 'date', 'git_reference', 'complexity',
    )
    list_filter = (
        'project', 'date',
    )
    ordering = ['project__name', '-date', ]

    def complexity(self, obj):
        try:
            complexity = obj.metrics['complexity']
        except (TypeError, KeyError):
            complexity = None

        return complexity
