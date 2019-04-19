from django.db import models

class CodeMetric(models.Model):
    project_slug = models.CharField(max_length=30)
    date = models.DateField()
    git_reference = models.CharField(max_length=30)

    complexity = models.IntegerField(null=True)
    loc = models.IntegerField(null=True)

    @property
    def complexity_per_loc(self):
        return self.complexity / self.loc

    class Meta:
        unique_together = (
            ('project_slug', 'date', 'git_reference'),
        )


class ExternalMetric(models.Model):
    project_slug = models.CharField(max_length=30)
    date = models.DateField()

    jira_bug_issues = models.IntegerField(null=True)
    gitlab_bug_issues = models.IntegerField(null=True)
    sentry_errors = models.IntegerField(null=True)

    class Meta:
        unique_together = (
            ('project_slug', 'date'),
        )
