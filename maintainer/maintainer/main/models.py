from django.contrib.postgres.fields import JSONField
from django.db import models


class Metric(models.Model):
    project_slug = models.CharField(max_length=40)
    date = models.DateField()
    git_reference = models.CharField(max_length=40, null=True)

    complexity = models.IntegerField(null=True)
    loc = models.IntegerField(null=True)

    jira_bug_issues = models.IntegerField(null=True)
    gitlab_bug_issues = models.IntegerField(null=True)
    sentry_errors = models.IntegerField(null=True)

    metrics = JSONField(null=True)

    @property
    def complexity_per_loc(self):
        return (self.complexity or 0) / (self.loc or 1)

    class Meta:
        unique_together = (
            ('project_slug', 'date'),
        )
