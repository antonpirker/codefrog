import os
from datetime import timedelta

import structlog
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import Count, Max, Min
from django.utils import timezone
from mptt.models import MPTTModel, TreeForeignKey

from core.mixins import GithubMixin
from core.utils import date_range, run_shell_command, log
from engine.models import CodeChange

logger = structlog.get_logger(__name__)

STATUS_READY = 1
STATUS_QUEUED = 2
STATUS_UPDATING = 3

STATUS_CHOICES = (
    (STATUS_READY, 'ready'),
    (STATUS_QUEUED, 'queued'),
    (STATUS_UPDATING, 'updating'),
)

# Possibly nice projects to import:
"""
Angular	https://github.com/angular/angular
Bitcoin	https://github.com/bitcoin/bitcoin
Certbot	https://github.com/certbot/certbot
codefrog https://github.com/codefroghq/codefrog.git
Covid-19 App of WHO https://github.com/WorldHealthOrganization/app
Elasticsearch https://github.com/elastic/elasticsearch
Hugo https://github.com/gohugoio/hugo.git
Kubernetes https://github.com/kubernetes/kubernetes.git
Letsencrypt Boulder	https://github.com/letsencrypt/boulder
React https://github.com/facebook/react
Tensorflow https://github.com/tensorflow/tensorflow
Visual Studio Code https://github.com/Microsoft/vscode.git
Vue.js https://github.com/vuejs/vue
ZEIT Now https://github.com/zeit/now
"""

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

    status = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_READY)

    last_update = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.name} ({self.pk})'

    @property
    def repo_dir(self):
        return os.path.join(settings.PROJECT_SOURCE_CODE_DIR, self.github_repo_name)

    @property
    def log_history(self):
        return self.logentry_set.all()[:30]

    @property
    def current_source_status(self):
        return self.source_stati.order_by('timestamp').last()

    def ingest(self):
        """
        Import all historical data of the project.
        """
        from celery import chain, group
        from connectors.git.tasks import clone_repo, import_code_changes, import_tags
        from core.tasks import save_last_update, get_source_status, \
            update_source_status_with_complexity, update_source_status_with_ownership, \
            update_source_status_with_changes
        from engine.tasks import calculate_code_metrics, calculate_issue_metrics
        from connectors.github.tasks import import_issues, import_releases

        self.status = STATUS_QUEUED
        self.save()

        ingest_project = chain(
            clone_repo.s(),
            group(
                import_code_changes.s(),
                chain(
                    get_source_status.s(),
                    update_source_status_with_complexity.s(),
                    update_source_status_with_ownership.s(),
                ),
            ),
            update_source_status_with_changes.s(),
            group(
                calculate_code_metrics.s(),  # TODO: calculate_code_metrics calculates complexity and change frequency for the whole project. We do not need the change frequency at the moment, may delete? (can not be run in parallel)
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
        """
        Import new data from the last 24 hours.
        """
        from celery import chain, group
        from connectors.git.tasks import clone_repo, import_code_changes, import_tags
        from core.tasks import save_last_update, get_source_status, \
            update_source_status_with_complexity, update_source_status_with_ownership, \
            update_source_status_with_changes
        from engine.tasks import calculate_code_metrics, calculate_issue_metrics
        from connectors.github.tasks import import_issues, import_open_issues, \
            import_releases

        start_date = (timezone.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        log(self.pk, 'Project update', 'start')
        self.status = STATUS_QUEUED
        self.save()

        update_project = chain(
            clone_repo.s(),
            group(
                import_code_changes.s(start_date=start_date),
                chain(
                    get_source_status.s(),
                    update_source_status_with_complexity.s(),
                    update_source_status_with_ownership.s(),
                ),
            ),
            update_source_status_with_changes.s(),

            group(
                calculate_code_metrics.s(start_date=start_date),  # TODO: calculate_code_metrics calculates complexity and change frequency for the whole project. We do not need the change frequency at the moment, may delete? (can not be run in parallel)
                chain(
                    import_open_issues.s(),
                    import_issues.s(start_date=start_date),
                    calculate_issue_metrics.s(),
                ),
                import_releases.s(),
                import_tags.s(),
            ),
            save_last_update.s(),
        )
        update_project.apply_async((self.pk, ))

    def purge(self):
        """
        Delete all imported data but not the project itself.
        """
        from core.models import Metric, Release, Complexity
        from engine.models import CodeChange, Issue, OpenIssue

        Release.objects.filter(project=self).delete()
        Metric.objects.filter(project=self).delete()
        OpenIssue.objects.filter(project=self).delete()
        CodeChange.objects.filter(project=self).delete()
        Issue.objects.filter(project=self).delete()
        Complexity.objects.filter(project=self).delete()
        LogEntry.objects.filter(project=self).delete()
        SourceStatus.objects.filter(project=self).delete()

        self.last_update = None
        self.status = STATUS_READY
        self.save()

    def clone_repo(self):
        from connectors.git.tasks import clone_repo
        clone_repo(
            project_id=self.pk,
        )

    def import_code_changes(self, start_date=None):
        from connectors.git.tasks import import_code_changes
        import_code_changes(
            project_id=self.pk,
            start_date=start_date,
        )

    def calculate_code_metrics(self, start_date=None):
        from engine.tasks import calculate_code_metrics
        calculate_code_metrics(
            project_id=self.pk,
            start_date=start_date,
        )

    def import_issues(self, start_date=None):
        from connectors.github.tasks import import_issues
        import_issues(
            project_id=self.pk,
            start_date=start_date,
        )

    def import_open_issues(self):
        from connectors.github.tasks import import_open_issues
        import_open_issues(
            project_id=self.pk,
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
            if complexity == 0:
                complexity = 1
        except (KeyError, AttributeError):
            complexity = 0

        try:
            ref_complexity = ref_metric.metrics['complexity']
            if ref_complexity == 0:
                ref_complexity = 1
        except (KeyError, AttributeError):
            ref_complexity = 1

        change = complexity/ref_complexity*100 - 100

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
        return SourceNode.objects.get(source_status=self.current_source_status, path=path).json_representation

    def get_file_ownership(self, path):
        file_metrics = self.get_file_metrics(path)
        return file_metrics['ownership']

    def get_file_commit_count(self, path, days):
        cmd = (
            f'git shortlog --summary --numbered --since="{days} days" HEAD -- "{path}"'
        )
        output = run_shell_command(cmd, cwd=self.repo_dir)
        lines = [line for line in output.split('\n') if line]

        commit_counts = {}
        for line in lines:
            commit_count, author = line.strip().split('\t', 1)
            commit_counts[author] = int(commit_count)

        return commit_counts


class LogEntry(models.Model):
    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
    )
    timestamp_start = models.DateTimeField()
    timestamp_end = models.DateTimeField(null=True,)
    message = models.CharField(max_length=255)

    def __str__(self):
        return f'{self.project} {self.message} ({self.timestamp_start} - {self.timestamp_end})'

    class Meta:
        ordering = ['-timestamp_start']


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


class SourceStatus(models.Model):
    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
        related_name='source_stati',
    )
    timestamp = models.DateTimeField()
    @property
    def tree(self):
        def render_tree(node):
            current_node = node.json_representation
            for child in node.get_children():
                current_node['children'].append(render_tree(child))

            return current_node

        root = SourceNode.objects.get(source_status=self, parent__isnull=True)
        return render_tree(root)

    @property
    def min_changes(self):
        return SourceNode.objects.filter(source_status=self)\
            .aggregate(Min('changes')).get('changes__min', 1)

    @property
    def max_changes(self):
        return SourceNode.objects.filter(source_status=self)\
            .aggregate(Max('changes')).get('changes__max', 1)

    @property
    def min_complexity(self):
        return SourceNode.objects.filter(source_status=self)\
            .aggregate(Min('complexity')).get('complexity__min', 1)

    @property
    def max_complexity(self):
        return SourceNode.objects.filter(source_status=self)\
            .aggregate(Max('complexity')).get('complexity__max', 1)

    def __str__(self):
        return f'{self.project} on {self.timestamp}'


class SourceNode(MPTTModel):
    source_status = models.ForeignKey(
        'SourceStatus',
        on_delete=models.CASCADE,
    )

    name = models.CharField(max_length=255)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    path = models.CharField(max_length=255, null=False, default='')
    repo_link = models.CharField(max_length=255, null=False, default='')

    complexity = models.PositiveIntegerField(null=False, default=1)
    changes = models.PositiveIntegerField(null=False, default=1)
    ownership = JSONField(null=False, default=[])

    def __str__(self):
        return self.name

    @property
    def json_representation(self):
        representation = {
            "name": self.name,

            "path": self.path,
            "repo_link": self.repo_link,

            "size": self.complexity,
            "changes": self.changes,
            "ownership": self.ownership,

            "children": [],
        }

        return representation

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        unique_together = [['parent', 'name']]


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
