import logging
import os
from datetime import timedelta

from celery import chain, group
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import Count
from django.utils import timezone

from core.mixins import GithubMixin
from core.utils import date_range, run_shell_command
from ingest.models import RawCodeChange

logger = logging.getLogger(__name__)


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    github_app_installation_refid = models.IntegerField(null=True)


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
        return os.path.join(settings.PROJECT_SOURCE_CODE_DIR, self.github_repo_name)

    def import_data(self):
        from ingest.tasks.git import clone_repo, ingest_code_metrics, ingest_git_tags
        from ingest.tasks.github import ingest_github_releases, import_past_github_issues

        clone = clone_repo.s(
            project_id=self.pk,
            git_url=self.git_url,
            repo_dir=self.repo_dir,
        )

        ingest_jobs = [
            ingest_code_metrics.s(
                repo_dir=self.repo_dir,
            ),

            ingest_git_tags.s(
                repo_dir=self.repo_dir,
            ),

            import_past_github_issues.s(
                repo_owner=self.github_repo_owner,
                repo_name=self.github_repo_name,
            ),
        ]

        if self.on_github:
            ingest_jobs.append(
                ingest_github_releases.s(
                    repo_owner=self.github_repo_owner,
                    repo_name=self.github_repo_name,
                ),
            )

        ingest = group(ingest_jobs)

        chain(clone, ingest).apply_async()

        self.last_update = timezone.now()
        self.save()

    def update_data(self):
        from ingest.tasks.git import clone_repo, ingest_code_metrics, ingest_git_tags
        from ingest.tasks.github import ingest_github_releases, import_open_github_issues

        clone = clone_repo.s(
            project_id=self.pk,
            git_url=self.git_url,
            repo_dir=self.repo_dir,
        )

        ingest_jobs = [
            ingest_code_metrics.s(
                repo_dir=self.repo_dir,
                start_date=self.last_update,
            ),

            ingest_git_tags.s(
                repo_dir=self.repo_dir,
            ),

            import_open_github_issues.s(
                repo_owner=self.github_repo_owner,
                repo_name=self.github_repo_name,
            )
        ]

        if self.on_github:
            ingest_jobs.append(
                ingest_github_releases.s(
                    repo_owner=self.github_repo_owner,
                    repo_name=self.github_repo_name,
                ),
            )

        ingest = group(ingest_jobs)

        chain(clone, ingest).apply_async()

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

    def import_past_github_issues(self, start_date=None):
        from ingest.tasks.github import import_past_github_issues
        import_past_github_issues(
            project_id=self.pk,
            repo_owner=self.github_repo_owner,
            repo_name=self.github_repo_name,
            start_date=start_date,
        )

    def import_open_github_issues(self):
        from ingest.tasks.github import import_open_github_issues
        import_open_github_issues(
            project_id=self.pk,
            repo_owner=self.github_repo_owner,
            repo_name=self.github_repo_name,
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

    def get_complexity_change(self, days=30):
        ref_date = timezone.now() - timedelta(days=30)
        ref_metric = Metric.objects.filter(project=self, date__lte=ref_date)\
            .order_by('date')\
            .last()
        metric = Metric.objects.filter(project=self).order_by('date').last()
        change = metric.metrics['complexity']/ref_metric.metrics['complexity']*100 - 100

        print('ref_metric: %s' % ref_metric.metrics['complexity'])
        print('metric: %s' % metric.metrics['complexity'])
        print('change: %s' % change)

        return change

    def get_file_complexity_trend(self, path, days=30):
        """
        Return an array of complexities for the given path over the given days.

        :param path: The file for which the complexities should be returned.
        :param days: The number of days from today into the past.
        :return: Array of integers
        """
        today = timezone.now().date()
        ref_date = today - timedelta(days=days)

        complexities = {}
        for day in date_range(ref_date, today):
            complexities[day.strftime('%Y%m%d')] = 0

        metrics = Metric.objects.filter(
            project=self,
            file_path=path,
            date__gte=ref_date,
        ).order_by('date')

        for metric in metrics:
            date_string = metric.timestamp.strftime('%Y%m%d')
            complexities[date_string] += metric.complexity_added
            complexities[date_string] -= metric.complexity_removed

        trend = [x[1] for x in sorted(complexities.items())]
        return trend

    def get_file_changes_trend(self, path, days=30):
        """
        Return an array of code change for the given path over the given days.

        :param path: The file for which the code changes should be returned.
        :param days: The number of days from today into the past.
        :return: Array of integers
        """
        today = timezone.now().date()
        ref_date = today - timedelta(days=days)

        changes = {}
        for day in date_range(ref_date, today):
            changes[day.strftime('%Y%m%d')] = 0

        raw_changes = RawCodeChange.objects.filter(
                project=self,
                file_path=path,
                timestamp__gte=ref_date,
            )\
            .extra(select={'day': "TO_CHAR(timestamp, 'YYYYMMDD')"})\
            .values('day')\
            .annotate(changes=Count('timestamp'))

        for raw_change in raw_changes:
            changes[raw_change['day']] = raw_change['changes']

        trend = [x[1] for x in sorted(changes.items())]
        return trend

    def get_file_ownership(self, path):
        cmd = (
            f'git blame {path} | cut -d "(" -f 2 | cut -d " " -f "1,2" | sort | uniq -c'
        )
        output = run_shell_command(cmd, cwd=self.repo_dir)
        lines = [line for line in output.split('\n') if line]

        ownership = {}
        for line in lines:
            num_lines, author = line.strip().split(' ', 1)
            ownership[author] = int(num_lines)

        return ownership

    def get_file_commit_count(self, path):
        cmd = (
            f'git shortlog -s -- {path}'
        )
        output = run_shell_command(cmd, cwd=self.repo_dir)
        lines = [line for line in output.split('\n') if line]

        commit_counts = {}
        for line in lines:
            commit_count, author = line.strip().split('\t', 1)
            commit_counts[author] = int(commit_count)

        return commit_counts


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


class Usage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_index=True,
    )
    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
        db_index=True,
    )
    timestamp = models.DateTimeField(db_index=True)
    action = models.CharField(max_length=100, blank=False, db_index=True)
