from django.contrib.postgres.fields import ArrayField
from django.db import models


class CodeChange(models.Model):
    project = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
    )
    timestamp = models.DateTimeField()
    file_path = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    complexity_added = models.PositiveIntegerField()
    complexity_removed = models.PositiveIntegerField()
    description = models.TextField(null=False, default='')
    git_commit_hash = models.CharField(max_length=255, null=False, default='')


class Issue(models.Model):
    project = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
    )
    issue_refid = models.CharField(max_length=100)
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True)

    labels = ArrayField(
        models.CharField(max_length=255),
        default=list,
    )

    def get_age(self, at_date=None):
        if self.closed_at and at_date:
            closed = min(self.closed_at, at_date)
        else:
            closed = self.closed_at or at_date

        closed = closed.replace(hour=0, minute=0, second=0, microsecond=0)
        opened = self.opened_at.replace(hour=0, minute=0, second=0, microsecond=0)

        return (closed-opened).days

    class Meta:
        unique_together = (
            ('project', 'issue_refid', ),
        )


class OpenIssue(models.Model):
    project = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
    )
    query_time = models.DateTimeField()

    issue_refid = models.CharField(max_length=100)

    labels = ArrayField(
        models.CharField(max_length=255),
        default=list,
    )


class PullRequest(models.Model):
    project = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
    )
    pull_request_refid = models.CharField(max_length=100)
    opened_at = models.DateTimeField()
    merged_at = models.DateTimeField(null=True)
    age = models.IntegerField(null=True)

    class Meta:
        unique_together = (
            ('project', 'pull_request_refid', ),
        )
