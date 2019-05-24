import os

from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models

from core.utils import run_shell_command
from ingest.git import ingest_code_metrics
from ingest.github import ingest_github_issues


class Project(models.Model):
    slug = models.SlugField(max_length=40)
    name = models.CharField(max_length=100)
    git_url = models.CharField(max_length=255)

    external_services = JSONField(null=True)

    def __str__(self):
        return self.name

    @property
    def repo_name(self):
        return self.git_url.rpartition('/')[2].replace('.git', '')

    @property
    def repo_dir(self):
        return os.path.join('/git_projects', self.repo_name)

    @property
    def has_github_issues(self):
        return 'github_issues' in self.external_services

    def clone_repo(self):
        """
        Clone the remote git repository to local directory.

        If the directory already exists only a `git pull` is done.

        :return: None
        """
        if os.path.exists(self.repo_dir):
            cmd = f'git pull'
            run_shell_command(cmd, cwd=self.repo_dir)
            return

        cmd = f'git clone {self.git_url} {self.repo_dir}'
        run_shell_command(cmd)

    def import_data(self, start_date=None):
        ingest_code_metrics(self.pk, self.repo_dir, start_date)

        if self.has_github_issues:
            ingest_github_issues(self.pk, start_date)



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
