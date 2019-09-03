import logging
import os

from celery import chain, group
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models, connection
from django.utils import timezone

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
        return os.path.join(settings.GIT_REPO_DIR, self.repo_name)

    @property
    def repo_url(self):
        url = None
        if self.has_github_issues:
            url = f'https://github.com/{self.github_repo_owner}/{self.github_repo_name}/'
        return url

    @property
    def github_repo_owner(self):
        return self.external_services['github_issues']['repo_owner'] \
            if 'github_issues' in self.external_services else None

    @property
    def github_repo_name(self):
        return self.external_services['github_issues']['repo_name'] \
            if 'github_issues' in self.external_services else None

    @property
    def has_github_issues(self):
        return 'github_issues' in self.external_services

    def import_data(self, start_date=None):
        from ingest.tasks.git import clone_repo, ingest_code_metrics, ingest_git_tags
        from ingest.tasks.github import ingest_github_issues
        from ingest.tasks.github import ingest_github_releases
        from ingest.tasks.github import update_github_issues

        update_from = start_date or self.last_update

        clone = clone_repo.s(
            project_id=self.pk,
            git_url=self.git_url,
            repo_dir=self.repo_dir,
        )

        ingest = group(
            ingest_code_metrics.s(
                repo_dir=self.repo_dir,
                start_date=update_from,
            ),

            ingest_git_tags.s(
                repo_dir=self.repo_dir,
            ),
        )

        chain(clone, ingest).apply_async()

        if self.has_github_issues:
            if update_from:
                update_github_issues.apply_async(
                    kwargs={
                        'project_id': self.pk,
                        'repo_owner': self.github_repo_owner,
                        'repo_name': self.github_repo_name,
                        'start_date': update_from,
                    }
                )
            else:
                ingest_github_issues.apply_async(
                    kwargs={
                        'project_id': self.pk,
                        'repo_owner': self.github_repo_owner,
                        'repo_name': self.github_repo_name,
                    }
                )

            ingest_github_releases.apply_async(
                kwargs={
                    'project_id': self.pk,
                    'repo_owner': self.github_repo_owner,
                    'repo_name': self.github_repo_name,
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
