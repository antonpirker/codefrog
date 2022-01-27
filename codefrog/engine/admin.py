from django.contrib import admin

from engine.models import CodeChange, Issue, OpenIssue


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "issue_refid",
        "opened_at",
        "closed_at",
        "labels",
    )
    list_filter = (
        "project",
        "opened_at",
    )
    ordering = ["project", "-opened_at"]


@admin.register(OpenIssue)
class OpenIssueAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "query_time",
        "issue_refid",
        "labels",
    )
    list_filter = ("project",)
    ordering = ["project", "-query_time"]


@admin.register(CodeChange)
class CodeChangeAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "file_path",
        "git_commit_hash",
        "author",
        "complexity_added",
        "complexity_removed",
        "timestamp",
    )
    list_filter = (
        "project",
        "timestamp",
    )
    ordering = ["project", "-timestamp"]
