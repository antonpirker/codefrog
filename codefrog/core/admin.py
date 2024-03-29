from django.contrib import admin
from django.contrib.postgres import fields
from django_json_widget.widgets import JSONEditorWidget
from mptt.admin import MPTTModelAdmin

from core.models import Project, Metric, Release, LogEntry
from core.models import SourceNode


class ModelAdminWithJSONWidget(admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {"widget": JSONEditorWidget},
    }


@admin.register(Project)
class ProjectAdmin(ModelAdminWithJSONWidget):
    list_display = (
        "id",
        "name",
        "user",
        "active",
        "status",
        "last_update",
    )
    list_filter = ("user", "active", "status")

    ordering = ("-id",)

    prepopulated_fields = {"slug": ("name",)}

    actions = [
        "import_project",
        "update_project",
    ]

    def import_project(self, request, queryset):
        for project in queryset:
            project.ingest()
            self.message_user(request, f"Import of {project.name} started.")

    import_project.short_description = "Initial import of project"

    def update_project(self, request, queryset):
        for project in queryset:
            project.update()
            self.message_user(request, f"Update of {project.name} started.")

    update_project.short_description = "Update project"


@admin.register(LogEntry)
class LogEntryAdmin(ModelAdminWithJSONWidget):
    list_display = (
        "project",
        "timestamp_start",
        "timestamp_end",
        "message",
    )
    list_filter = (
        "project",
        "message",
    )
    ordering = [
        "-timestamp_start",
    ]


@admin.register(Metric)
class MetricAdmin(ModelAdminWithJSONWidget):
    list_display = (
        "project",
        "date",
        "complexity",
    )
    list_filter = (
        "project",
        "date",
    )
    ordering = [
        "project__name",
        "-date",
    ]

    def complexity(self, obj):
        try:
            complexity = obj.metrics["complexity"]
        except (TypeError, KeyError):
            complexity = None

        return complexity


@admin.register(Release)
class ReleaseAdmin(ModelAdminWithJSONWidget):
    list_display = (
        "project",
        "timestamp",
        "name",
        "type",
        "url",
    )
    list_filter = (
        "project",
        "timestamp",
    )
    ordering = [
        "project__name",
        "-timestamp",
    ]


@admin.register(SourceNode)
class SourceNodeAdmin(MPTTModelAdmin):
    list_filter = (
        "source_status__project",
        "source_status",
    )
