from django.contrib import admin
from django.contrib.postgres import fields

from django_json_widget.widgets import JSONEditorWidget

from core.models import Project, Metric, Release
from web.models import Usage


@admin.register(Usage)
class UsageAdmin(admin.ModelAdmin):
    list_display = (
        'project', 'user', 'timestamp', 'action',
    )
    list_filter = (
        'project', 'user', 'timestamp', 'action',
    )
    ordering = ['-timestamp', ]
