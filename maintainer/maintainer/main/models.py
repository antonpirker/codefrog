from django.db import models

class Metric(models.Model):
    project_slug = models.CharField(max_length=30)
    git_reference = models.CharField(max_length=30)
    date = models.DateField()
    metric = models.IntegerField()

    class Meta:
        unique_together = (
            ('project_slug', 'date', 'git_reference'),
        )
