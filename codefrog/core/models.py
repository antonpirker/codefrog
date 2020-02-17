import logging
import os
from datetime import timedelta

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import Count
from django.utils import timezone

from core.mixins import GithubMixin
from core.utils import date_range, run_shell_command
from engine.models import CodeChange

logger = logging.getLogger(__name__)


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
    source_tree_metrics = JSONField(null=True)

    last_update = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.name} ({self.pk})'

    @property
    def repo_dir(self):
        return os.path.join(settings.PROJECT_SOURCE_CODE_DIR, self.github_repo_name)

    def ingest(self):
        from celery import chain, group
        from connectors.git.tasks import clone_repo, import_code_changes, import_tags
        from connectors.github.tasks import import_issues, import_releases
        from core.tasks import get_source_tree_metrics, save_last_update
        from engine.tasks import calculate_code_metrics, calculate_issue_metrics

        ingest_project = chain(
            clone_repo.s(),
            import_code_changes.s(),  # TODO: performance: should be called with massive parallelization to be fast (see TODOs in import_code_changes)
            group(
                calculate_code_metrics.s(),  # TODO: calculate_code_metrics calculates complexity and change frequency for the whole project. We do not need the change frequency at the moment, may delete? (can not be run in parallel)
                get_source_tree_metrics.s(),  # TODO: see TODOs in get_source_tree_metrics for optimization
                chain(
                    import_issues.s(),
                    calculate_issue_metrics.s(),
                ),
                import_releases.s(),
                import_tags.s(),
            ),
            save_last_update.s(),
        )
        ingest_project.apply_async((self.pk, ))

    def update(self):
        # TODO: import everything from the last 24 hours.
        from celery import chain, group
        from connectors.git.tasks import clone_repo, import_code_changes, import_tags
        from connectors.github.tasks import import_issues, import_releases
        from core.tasks import get_source_tree_metrics, save_last_update
        from engine.tasks import calculate_code_metrics, calculate_issue_metrics

        start_date = timezone.now() - timedelta(days=1)

        update_project = chain(
            clone_repo.s(),
            import_code_changes.s(start_date=start_date),  # TODO: performance: should be called with massive parallelization to be fast (see TODOs in import_code_changes)
            save_last_update.s(),
        )
        update_project.apply_async((self.pk, ))

    def purge(self):
        from core.models import Metric, Release, Complexity
        from engine.models import CodeChange, Issue, OpenIssue

        Release.objects.filter(project=self).delete()
        Metric.objects.filter(project=self).delete()
        OpenIssue.objects.filter(project=self).delete()
        CodeChange.objects.filter(project=self).delete()
        Issue.objects.filter(project=self).delete()
        Complexity.objects.filter(project=self).delete()
        self.source_tree_metrics = {}
        self.last_update = None
        self.save()

    def clone_repo(self):
        from connectors.git.tasks import clone_repo
        clone_repo(
            project_id=self.pk,
            git_url=self.git_url,
            repo_dir=self.repo_dir,
        )

    def import_code_changes(self):
        from connectors.git.tasks import import_code_changes
        import_code_changes(
            project_id=self.pk,
            repo_dir=self.repo_dir,
        )

    def calculate_code_metrics(self):
        from engine.tasks import calculate_code_metrics
        calculate_code_metrics(
            project_id=self.pk,
        )

    def get_source_tree_metrics(self):
        from core.tasks import get_source_tree_metrics
        get_source_tree_metrics(
            project_id=self.pk,
        )

    def import_issues(self, start_date=None):
        from connectors.github.tasks import import_issues
        import_issues(
            project_id=self.pk,
            repo_owner=self.github_repo_owner,
            repo_name=self.github_repo_name,
            start_date=start_date,
        )

    def import_open_issues(self):
        from connectors.github.tasks import import_open_issues
        import_open_issues(
            project_id=self.pk,
            repo_owner=self.github_repo_owner,
            repo_name=self.github_repo_name,
        )

    def calculate_issue_metrics(self):
        from engine.tasks import calculate_issue_metrics
        calculate_issue_metrics(
            project_id=self.pk
        )
    def import_releases(self):
        from connectors.github.tasks import import_releases
        import_releases(
            project_id=self.pk,
            repo_owner=self.github_repo_owner,
            repo_name=self.github_repo_name,
        )

    def import_tags(self):
        from connectors.git.tasks import import_tags
        import_tags(
            project_id=self.pk,
        )

    def get_complexity_change(self, days=30):
        ref_date = timezone.now() - timedelta(days=days)
        ref_metric = Metric.objects.filter(project=self, date__lte=ref_date)\
            .order_by('date')\
            .last()
        metric = Metric.objects.filter(project=self).order_by('date').last()

        try:
            complexity = metric.metrics['complexity']
        except (KeyError, AttributeError):
            complexity = 0

        try:
            ref_complexity = metric.metrics['complexity']
        except (KeyError, AttributeError):
            ref_complexity = 1

        change = complexity/ref_complexity*100 - 100

        print('ref_metric: %s' % ref_complexity)
        print('metric: %s' % complexity)
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

        try:
            ref_complexity = Complexity.objects.filter(
                project=self,
                file_path=path,
                timestamp__lte=ref_date,
            ).order_by('-timestamp').first().complexity
        except AttributeError:
            ref_complexity = 0

        complexities = {}
        for day in date_range(ref_date, today):
            complexities[day.strftime('%Y%m%d')] = ref_complexity

        comps = Complexity.objects.filter(
            project=self,
            file_path=path,
            timestamp__gte=ref_date,
        ).order_by('timestamp')

        for comp in comps:
            complexities[comp.timestamp.strftime('%Y%m%d')] = comp.complexity

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

        raw_changes = CodeChange.objects.filter(
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

    def get_file_metrics(self, path):
        def get_child(nodes, child_path):
            for node in nodes:
                if 'children' in node.keys():
                    found_node = get_child(node['children'], child_path)
                    if found_node:
                        return found_node
                else:
                    if 'path' in node.keys() and node['path'] == child_path:
                        return node

        return get_child(self.source_tree_metrics['tree']['children'], path)

    def get_file_ownership(self, path):
        file_metrics = self.get_file_metrics(path)
        return file_metrics['ownership']

    def get_file_commit_count(self, path, days):
        cmd = (
            f'git shortlog --summary --since="{days} days" -- {path}'
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

    def __str__(self):
        return f'{self.name} ({self.pk})'


class Complexity(models.Model):
    project = models.ForeignKey(
        'core.Project',
        on_delete=models.CASCADE,
    )
    timestamp = models.DateTimeField()
    file_path = models.CharField(max_length=255)
    complexity = models.PositiveIntegerField()
