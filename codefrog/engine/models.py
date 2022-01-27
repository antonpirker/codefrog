import datetime
import re

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

from engine.mixins import CategorizationMixin, CATEGORY_CHOICES, CATEGORY_CHANGE


class CodeChange(models.Model):
    project = models.ForeignKey(
        "core.Project",
        on_delete=models.CASCADE,
        related_name="code_changes",
    )
    issue = models.OneToOneField(
        "engine.Issue",
        null=True,
        on_delete=models.SET_NULL,
        related_name="code_change",
    )
    timestamp = models.DateTimeField()
    file_path = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    complexity_added = models.PositiveIntegerField()
    complexity_removed = models.PositiveIntegerField()
    description = models.TextField(null=False, default="")
    git_commit_hash = models.CharField(max_length=255, null=False, default="")

    def save(self, *args, **kwargs):
        issue_refid = None
        regex_issue_number = r"#[0-9]{1,8}"
        search_object = re.search(regex_issue_number, self.description)
        if search_object:
            issue_refid = search_object.group(0)

        regex_issue_number_other_repo = r"[\w-]+\/[\w-]+#[0-9]{1,8}"
        search_object = re.search(regex_issue_number_other_repo, self.description)
        if search_object:
            issue_refid = search_object.group(0)

        if not issue_refid:
            return

        if issue_refid.startswith("#"):
            self.issue = self.project.issue_set.filter(
                issue_refid=issue_refid[1:]
            ).first()
        else:
            # TODO: implement links to other repositories
            raise NotImplemented(
                "References to issues in other repositories is currently not implemented."
            )

        super().save(*args, **kwargs)


class Issue(CategorizationMixin, models.Model):
    project = models.ForeignKey(
        "core.Project",
        on_delete=models.CASCADE,
        related_name="issues",
    )
    issue_refid = models.CharField(max_length=100)
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True)

    labels = ArrayField(
        models.CharField(max_length=255),
        default=list,
    )
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_CHANGE
    )

    def __str__(self):
        return f"Issue #{self.issue_refid} ({self.pk})"

    def get_age(self, at_date=None):
        if self.closed_at and at_date:
            closed = min(
                self.closed_at,
                timezone.make_aware(
                    datetime.datetime.combine(at_date, datetime.time.max)
                ),
            )
        else:
            closed = self.closed_at or at_date

        closed = (
            closed.replace(hour=0, minute=0, second=0, microsecond=0).date()
            if isinstance(closed, datetime.datetime)
            else closed
        )
        opened = (
            self.opened_at.replace(hour=0, minute=0, second=0, microsecond=0).date()
            if isinstance(self.opened_at, datetime.datetime)
            else self.opened_at
        )

        return (closed - opened).days

    class Meta:
        unique_together = (
            (
                "project",
                "issue_refid",
            ),
        )


class OpenIssue(models.Model):
    project = models.ForeignKey(
        "core.Project",
        on_delete=models.CASCADE,
    )
    query_time = models.DateTimeField()

    issue_refid = models.CharField(max_length=100)

    labels = ArrayField(
        models.CharField(max_length=255),
        default=list,
    )


class PullRequest(CategorizationMixin, models.Model):
    project = models.ForeignKey(
        "core.Project",
        on_delete=models.CASCADE,
    )
    pull_request_refid = models.CharField(max_length=100)
    opened_at = models.DateTimeField()
    merged_at = models.DateTimeField(null=True)
    age = models.IntegerField(null=True)

    labels = ArrayField(
        models.CharField(max_length=255),
        default=list,
    )
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_CHANGE
    )

    def __str__(self):
        return f"Pull Request #{self.pull_request_refid} ({self.pk})"

    class Meta:
        unique_together = (
            (
                "project",
                "pull_request_refid",
            ),
        )
