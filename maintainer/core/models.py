import logging
import os

from celery import chain, group
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils import timezone

from core.mixins import GithubMixin

logger = logging.getLogger(__name__)


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    github_app_installation_refid = models.IntegerField()


class Project(GithubMixin, models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='projects',
        null=True, blank=True,
    )
    private = models.BooleanField(default=True)
    active = models.BooleanField(default=False)
    source = models.CharField(max_length=10, blank=True, default='')
    slug = models.SlugField(max_length=255, unique=True)
    name = models.CharField(max_length=100)
    git_url = models.CharField(max_length=255)

    external_services = JSONField(null=True)

    last_update = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    @property
    def repo_dir(self):
        return os.path.join(settings.GIT_REPO_DIR, self.github_repo_name)

    def import_data(self, start_date=None):
        from ingest.tasks.git import clone_repo, ingest_code_metrics, ingest_git_tags
        from ingest.tasks.github import ingest_github_releases, ingest_raw_github_issues

        clone = clone_repo.s(
            project_id=self.pk,
            git_url=self.git_url,
            repo_dir=self.repo_dir,
        )

        ingest = group(
            ingest_code_metrics.s(
                repo_dir=self.repo_dir,
                start_date=start_date or self.last_update,
            ),

            ingest_git_tags.s(
                repo_dir=self.repo_dir,
            ),

            ingest_raw_github_issues.s(
                repo_owner=self.github_repo_owner,
                repo_name=self.github_repo_name,
            ),
        )

        chain(clone, ingest).apply_async()

        if self.on_github:
            ingest_github_releases.apply_async(
                kwargs={
                    'project_id': self.pk,
                    'repo_owner': self.github_repo_owner,
                    'repo_name': self.github_repo_name,
                }
            )

        self.last_update = timezone.now()
        self.save()

    def clone_repo(self):
        from ingest.tasks.git import clone_repo
        clone_repo(
            project_id=self.pk,
            git_url=self.git_url,
            repo_dir=self.repo_dir,
        )

    def ingest_code_metrics(self):
        from ingest.tasks.git import ingest_code_metrics
        ingest_code_metrics(
            project_id=self.pk,
            repo_dir=self.repo_dir,
        )

    def ingest_git_tags(self):
        from ingest.tasks.git import ingest_git_tags
        ingest_git_tags(
            project_id=self.pk,
            repo_dir=self.repo_dir,
        )

    def ingest_raw_github_issues(self, start_date=None):
        from ingest.tasks.github import ingest_raw_github_issues
        ingest_raw_github_issues(
            project_id=self.pk,
            repo_owner=self.github_repo_owner,
            repo_name=self.github_repo_name,
            start_date=start_date,
        )

    def ingest_open_github_issues(self):
        from ingest.tasks.github import ingest_open_github_issues
        ingest_open_github_issues(
            project_id=self.pk,
            repo_owner=self.github_repo_owner,
            repo_name=self.github_repo_name,
        )

    def ingest_github_releases(self):
        from ingest.tasks.github import ingest_github_releases
        ingest_github_releases(
            project_id=self.pk,
            repo_owner=self.github_repo_owner,
            repo_name=self.github_repo_name,
        )


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
