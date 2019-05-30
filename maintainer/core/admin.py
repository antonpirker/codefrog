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

    actions = ['import_project']

    def import_project(self, request, queryset):
        for project in queryset:
            project.clone_repo()
            project.import_data()
            self.message_user(request, f'Import of {project.name} started.')
    import_project.short_description = 'Import Project'


@admin.register(Metric)
class MetricAdmin(ModelAdminWithJSONWidget):
    list_display = (
        'project', 'date', 'complexity',
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
