
from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models


class Project(models.Model):
    slug = models.SlugField(max_length=40)
    name = models.CharField(max_length=100)
    source_dir = models.CharField(max_length=255)

    external_services = JSONField(null=True)

    def __str__(self):
        return self.name


class Metric(models.Model):
    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
    )
    date = models.DateField()
    git_reference = models.CharField(max_length=40, null=True)
    authors = ArrayField(
        models.CharField(max_length=100),
        default=list,
    )

    metrics = JSONField(null=True)

    @property
    def complexity_per_loc(self):
        complexity = self.metrics['complexity'] if 'complexity' in self.metrics else 0
        loc = self.metrics['loc'] if 'loc' in self.metrics else 1
        return complexity / loc

    class Meta:
        unique_together = (
            ('project', 'date'),
        )
