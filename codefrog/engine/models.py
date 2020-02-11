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
