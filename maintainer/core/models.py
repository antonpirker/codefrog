import os
import logging

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils import timezone

from core.utils import run_shell_command

logger = logging.getLogger(__name__)


class Project(models.Model):
    slug = models.SlugField(max_length=40)
    name = models.CharField(max_length=100)
    git_url = models.CharField(max_length=255)

    external_services = JSONField(null=True)

    last_update = models.DateTimeField(null=True, blank=True)

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
            logger.info('Start pulling new changes of %s.', self.slug)
            cmd = f'git pull'
            run_shell_command(cmd, cwd=self.repo_dir)
            logger.info('Finished pulling new changes of %s.', self.slug)
            return

        logger.info('Start cloning %s.', self.slug)
        cmd = f'git clone {self.git_url} {self.repo_dir}'
        run_shell_command(cmd)
        logger.info('Finished cloning %s.', self.slug)

    def import_data(self, start_date=None):
        from ingest.tasks.git import ingest_code_metrics, ingest_git_tags
        from ingest.tasks.github import ingest_github_issues
        from ingest.tasks.github import ingest_github_releases
        from ingest.tasks.github import update_github_issues

        update_from = start_date or self.last_update

        ingest_code_metrics.apply_async(
            kwargs={
                'project_id': self.pk,
                'repo_dir': self.repo_dir,
                'start_date': update_from,
            }
        )

        ingest_git_tags.apply_async(
            kwargs={
                'project_id': self.pk,
                'repo_dir': self.repo_dir,
            }
        )

        if self.has_github_issues:
            repo_owner = self.external_services['github_issues']['repo_owner'],
            repo_name = self.external_services['github_issues']['repo_name']

            if update_from:
                update_github_issues.apply_async(
                    kwargs={
                        'project_id': self.pk,
                        'repo_owner': repo_owner,
                        'repo_name': repo_name,
                        'start_date': update_from,
                    }
                )
            else:
                ingest_github_issues.apply_async(
                    kwargs={
                        'project_id': self.pk,
                        'repo_owner': repo_owner,
                        'repo_name': repo_name,
                    }
                )

            ingest_github_releases.apply_async(
                kwargs={
                    'project_id': self.pk,
                    'repo_owner': repo_owner,
                    'repo_name': repo_name,
                }
            )

        self.last_update = timezone.now()
        self.save()


class Metric(models.Model):
    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
    )
    date = models.DateField()
    file_path = models.CharField(max_length=255, blank=True)
    metrics = JSONField(null=True, blank=True)

    class Meta:
        unique_together = (
            ('project', 'date'),
        )


class Release(models.Model):
    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
    )
    timestamp = models.DateTimeField()
    type = models.CharField(max_length=20, default='git_tag')
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=255, blank=True)
