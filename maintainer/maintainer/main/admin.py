from django.contrib import admin
from django.contrib.postgres import fields

from django_json_widget.widgets import JSONEditorWidget

from maintainer.main.models import Project, Metric


class ModelAdminWithJSONWidget(admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget},
    }


@admin.register(Project)
class ProjectAdmin(ModelAdminWithJSONWidget):
    list_display = (
        'name', 'slug', 'source_dir',
    )
    ordering = ['name', ]

    prepopulated_fields = {'slug': ('name',)}


@admin.register(Metric)
class MetricAdmin(ModelAdminWithJSONWidget):
    list_display = (
        'project_name', 'date', 'git_reference',
    )
    ordering = ['project__name', '-date', ]

    def project_name(self, obj):
        return obj.project.name
