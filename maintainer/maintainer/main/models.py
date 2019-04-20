from django.contrib.postgres.fields import JSONField
from django.db import models


class Metric(models.Model):
    project_slug = models.CharField(max_length=40)
    date = models.DateField()
    git_reference = models.CharField(max_length=40, null=True)

    metrics = JSONField(null=True)

    @property
    def complexity_per_loc(self):
        return (self.metrics['complexity'] if 'complexity' in self.metrics else  0) / \
               (self.metrics['loc'] if 'loc' in self.metrics else 1)

    class Meta:
        unique_together = (
            ('project_slug', 'date'),
        )
