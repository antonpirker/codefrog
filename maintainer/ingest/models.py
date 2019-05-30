from django.contrib.postgres.fields import ArrayField
from django.db import models


class RawIssue(models.Model):
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

    class Meta:
        unique_together = (
            ('project', 'issue_refid', ),
        )


class RawCodeChange(models.Model):
    project = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
    )
    timestamp = models.DateTimeField()
    file_path = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    complexity_added = models.PositiveIntegerField()
    complexity_removed = models.PositiveIntegerField()
