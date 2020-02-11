import datetime
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
from ingest.models import CodeChange, Complexity

logger = logging.getLogger(__name__)


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    github_app_installation_refid = models.IntegerField(null=True)

    fastspring_subscription_refid = models.CharField(max_length=100, blank=True, default='')
    fastspring_account_refid = models.CharField(max_length=100, blank=True, default='')

    newly_registered = models.BooleanField(default=True)

    plan = models.ForeignKey(
        'Plan',
        on_delete=models.SET_NULL,
        db_index=True,
        null=True,
    )

    date_joined = models.DateTimeField(default=timezone.now, null=False)

    @property
    def plan_name_and_status(self):
        plan_name = f'{ self.plan.name } Plan'

        if self.plan.has_trial_period:
            expiration_date = self.date_joined + timedelta(days=self.plan.free_trial_days)

            if expiration_date >= timezone.now():
                plan_name = '%s (Free trial period until: %s)' % (
                    plan_name,
                    expiration_date.strftime('%B %d, %Y'),
                )
            else:
                plan_name = '%s (Free trial expired: %s)' % (
                    plan_name,
                    expiration_date.strftime('%B %d, %Y'),
                )

        return plan_name

    def __str__(self):
        return f'{self.user.username} ({self.pk})'


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

    def import_data(self):
#        self.clone_repo() # must be the first thing
#        self.import_code_changes()  # depends on clone_repo()  # TODO: see todos in import_code_changes for optimization
#        self.get_source_tree_metrics()  # depends on import_code_changes() NOT calculate_code_metrics
            # TODO: import_code_changes should be called first with massive parallelication, so it is fast.
            #  inside is then called calculate_code_metrics after import_code_changes is finished.
            #  get_source_tree_metrics can also be called at the same time as calculate_code_metrics (they do not depend on each other.) see todos in get_source_tree_metrics for optimization
            #  calculate_code_metrics calculates complexity and change frequency for the whole project. We do not need the change frequency at the moment, may delete? (can not be parallelolized)
        # self.calculate_code_metrics() # depends on import_code_changes() NOT get_source_tree_metrics

#        self.import_issues()  # async
#        self.import_github_releases()  # async, performance does not matter
#        self.import_tags()  # async, performance does not matter

        """
        from ingest.tasks.git import clone_repo, import_code_changes, ingest_git_tags
        from ingest.tasks.github import ingest_github_releases, import_issues

        clone = clone_repo.s(
            project_id=self.pk,
            git_url=self.git_url,
            repo_dir=self.repo_dir,
        )

        ingest_jobs = [
            import_code_changes.s(
                repo_dir=self.repo_dir,
            ),

            ingest_git_tags.s(
                repo_dir=self.repo_dir,
            ),

            import_issues.s(
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
        """

        #self.last_update = timezone.now()
        #self.save()

    def update_data(self):
        from ingest.tasks.git import clone_repo, import_code_changes, ingest_git_tags
        from ingest.tasks.github import ingest_github_releases, import_open_github_issues

        clone = clone_repo.s(
            project_id=self.pk,
            git_url=self.git_url,
            repo_dir=self.repo_dir,
        )

        ingest_jobs = [
            import_code_changes.s(
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

    def purge_data(self):
        from core.models import Metric, Release, Usage
        from ingest.models import Complexity, OpenIssue, CodeChange, Issue

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
        from ingest.tasks.git import clone_repo
        clone_repo(
            project_id=self.pk,
            git_url=self.git_url,
            repo_dir=self.repo_dir,
        )

    def import_code_changes(self):
        from ingest.tasks.git import import_code_changes
        import_code_changes(
            project_id=self.pk,
            repo_dir=self.repo_dir,
        )

    def get_source_tree_metrics(self):
        from core.tasks import get_source_tree_metrics
        get_source_tree_metrics(
            project_id=self.pk,
        )

    def import_issues(self, start_date=None):
        from ingest.tasks.github import import_issues
        import_issues(
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

    def import_github_releases(self):
        from ingest.tasks.github import import_github_releases
        import_github_releases(
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


class Usage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_index=True,
        null=True,
    )
    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
        db_index=True,
        null=True,
    )
    timestamp = models.DateTimeField(db_index=True)
    action = models.CharField(max_length=100, blank=False, db_index=True)


class Plan(models.Model):
    name = models.CharField(max_length=40)
    slug = models.CharField(max_length=40)
    has_trial_period = models.BooleanField(default=False)
    free_trial_days = models.IntegerField(default=14)

    def __str__(self):
        return f'{self.name} ({self.pk})'
