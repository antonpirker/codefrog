import os
import shutil
import tempfile
from contextlib import contextmanager
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
from settings import DEFAULT_TASK_EXPIRATION

logger = structlog.get_logger(__name__)

STATUS_READY = 1
STATUS_QUEUED = 2
STATUS_UPDATING = 3

STATUS_CHOICES = (
    (STATUS_READY, "ready"),
    (STATUS_QUEUED, "queued"),
    (STATUS_UPDATING, "updating"),
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
        related_name="projects",
        null=True,
        blank=True,
    )
    private = models.BooleanField(default=True)
    active = models.BooleanField(default=False)
    source = models.CharField(max_length=10, blank=True, default="")
    slug = models.SlugField(max_length=255, unique=True)
    name = models.CharField(max_length=100)
    git_url = models.CharField(max_length=255)
    git_branch = models.CharField(max_length=255, default="")

    external_services = JSONField(null=True)

    status = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_READY)

    last_update = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.pk})"

    @contextmanager
    def get_tmp_repo_dir(self):
        self.clone_repo()
        tmp_dir = tempfile.mkdtemp(dir="/dev/shm")  # in memory! yay!

        cmd = f'git clone --quiet --no-hardlinks "{self.repo_dir}" "{tmp_dir}"'
        run_shell_command(cmd)

        try:
            yield tmp_dir
        finally:
            shutil.rmtree(tmp_dir)

    @property
    def repo_dir(self):
        return os.path.join(settings.PROJECT_SOURCE_CODE_DIR, self.github_repo_name)

    @property
    def log_history(self):
        return self.logentry_set.all()[:30]

    @property
    def current_source_status(self):
        return self.get_source_status()

    def get_source_status(self, date=None):
        kwargs = {
            "active": True,
        }
        if date:
            kwargs["timestamp__date__lte"] = date

        return self.source_stati.filter(**kwargs).order_by("timestamp").last()

    def get_file_changes(self, date_from, date_to):
        changes = (
            CodeChange.objects.filter(
                project=self,
                timestamp__date__gte=date_from,
                timestamp__date__lte=date_to,
            )
            .values("file_path")
            .annotate(changes=Count("file_path"))
            .order_by("-changes", "file_path")
        )

        changes_dict = {x["file_path"]: x["changes"] for x in changes}
        all_nodes = SourceNode.objects.filter(source_status=self.current_source_status)
        all_paths = list(filter(None, list(set(x.project_path for x in all_nodes))))

        out = []
        for path in all_paths:
            out.append(
                {
                    "file_path": path,
                    "changes": changes_dict.get(path, 0),
                    "repo_link": self.get_repo_link(path),
                }
            )

        out.sort(key=lambda x: x["changes"], reverse=True)
        return out

    def get_repo_link(self, path):
        return f"{self.github_repo_url}/blame/master/{path}"

    def get_bug_labels(self):
        return [
            "bug",
            "Bug",
            "type:bug",
            "blocker",
            "breaking",
            "critical",
            "error",
            "failure",
            "issue",
            "regression",
            "won't fix",
            "wont-fix",
            "wontfix",
            "WontFix",
        ]

    def ingest(self):
        """
        Import all historical data of the project.
        """
        from celery import chain, group
        from connectors.git.tasks import clone_repo, import_code_changes, import_tags
        from core.tasks import (
            save_last_update,
            get_source_status,
            update_source_status_with_metrics,
        )
        from engine.tasks import (
            calculate_code_metrics,
            calculate_issue_metrics,
            calculate_pull_request_metrics,
        )
        from connectors.github.tasks import (
            import_issues,
            import_releases,
            import_pull_requests,
        )

        self.status = STATUS_QUEUED
        self.save()

        ingest_project = chain(
            # Clone Repo
            clone_repo.s().set(expires=DEFAULT_TASK_EXPIRATION),
            # Import git commits and at the same time all the data from GitHub.
            group(
                import_code_changes.s().set(expires=DEFAULT_TASK_EXPIRATION),
                chain(
                    import_issues.s().set(expires=DEFAULT_TASK_EXPIRATION),
                    calculate_issue_metrics.s().set(expires=DEFAULT_TASK_EXPIRATION),
                ),
                chain(
                    import_pull_requests.s().set(expires=DEFAULT_TASK_EXPIRATION),
                    calculate_pull_request_metrics.s().set(
                        expires=DEFAULT_TASK_EXPIRATION
                    ),
                ),
                import_releases.s().set(expires=DEFAULT_TASK_EXPIRATION),
                import_tags.s().set(expires=DEFAULT_TASK_EXPIRATION),
            ),
            # Calculate code metrics and at the same time the source status
            group(
                calculate_code_metrics.s().set(
                    expires=DEFAULT_TASK_EXPIRATION
                ),  # TODO: calculate_code_metrics calculates complexity and change frequency for the whole project. We do not need the change frequency at the moment, may delete? (can not be run in parallel)
                chain(
                    get_source_status.s().set(expires=DEFAULT_TASK_EXPIRATION),
                    update_source_status_with_metrics.s().set(
                        expires=DEFAULT_TASK_EXPIRATION
                    ),
                ),
            ),
            # Save last update date
            save_last_update.s().set(expires=DEFAULT_TASK_EXPIRATION),
        )

        ingest_project.apply_async((self.pk,))

    def update(self):
        """
        Import new data from the last 24 hours.
        """
        from celery import chain, group
        from connectors.git.tasks import clone_repo, import_code_changes, import_tags
        from core.tasks import (
            save_last_update,
            get_source_status,
            update_source_status_with_metrics,
        )
        from engine.tasks import (
            calculate_code_metrics,
            calculate_issue_metrics,
            calculate_pull_request_metrics,
        )
        from connectors.github.tasks import (
            import_issues,
            import_open_issues,
            import_releases,
            import_pull_requests,
        )

        start_date = (timezone.now() - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        log(self.pk, "Project update", "start")
        self.status = STATUS_QUEUED
        self.save()

        update_project = chain(
            clone_repo.s().set(expires=DEFAULT_TASK_EXPIRATION),
            group(
                import_code_changes.s(start_date=start_date),
                chain(
                    get_source_status.s().set(expires=DEFAULT_TASK_EXPIRATION),
                    update_source_status_with_metrics.s().set(
                        expires=DEFAULT_TASK_EXPIRATION
                    ),
                ),
            ),
            group(
                calculate_code_metrics.s(
                    start_date=start_date
                ),  # TODO: calculate_code_metrics calculates complexity and change frequency for the whole project. We do not need the change frequency at the moment, may delete? (can not be run in parallel)
                chain(
                    import_open_issues.s().set(expires=DEFAULT_TASK_EXPIRATION),
                    import_issues.s(start_date=start_date),
                    calculate_issue_metrics.s().set(expires=DEFAULT_TASK_EXPIRATION),
                ),
                chain(
                    import_pull_requests.s().set(expires=DEFAULT_TASK_EXPIRATION),
                    calculate_pull_request_metrics.s().set(
                        expires=DEFAULT_TASK_EXPIRATION
                    ),
                ),
                import_releases.s().set(expires=DEFAULT_TASK_EXPIRATION),
                import_tags.s().set(expires=DEFAULT_TASK_EXPIRATION),
            ),
            save_last_update.s().set(expires=DEFAULT_TASK_EXPIRATION),
        )
        update_project.apply_async((self.pk,))

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

    def delete_repo_dir(self):
        try:
            shutil.rmtree(self.repo_dir)
        except FileNotFoundError:
            pass

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

        calculate_issue_metrics(project_id=self.pk)

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

    def get_state_of_affairs(self, date_from, date_to):
        avg_issue_age = self.get_avg_issue_age(date_from, date_to)
        avg_pr_age = self.get_avg_pr_age(date_from, date_to)

        # get metrics of previous period
        days = (date_to - date_from).days
        date_from_past = date_from - timedelta(days=days)
        date_to_past = date_from
        avg_issue_age_past = self.get_avg_issue_age(date_from_past, date_to_past)
        avg_pr_age_past = self.get_avg_pr_age(date_from_past, date_to_past)

        state_of_affairs = {
            "complexity_change": self.get_complexity_change(date_from, date_to),
            "issue_age": avg_issue_age,
            "issue_age_change": self.get_value_change(
                avg_issue_age_past, avg_issue_age
            ),
            "pr_age": avg_pr_age,
            "pr_age_change": self.get_value_change(avg_pr_age_past, avg_pr_age),
        }

        return state_of_affairs

    def get_value_change(self, old_value, new_value):
        old_value = old_value if old_value != 0 else 1
        new_value = new_value if new_value != 0 else 1
        change = new_value / old_value * 100 - 100
        return change

    def get_complexity_change(self, date_from, date_to):
        ref_metric = (
            Metric.objects.filter(project=self, date__lte=date_from)
            .order_by("date")
            .last()
        )
        metric = (
            Metric.objects.filter(project=self, date__lte=date_to)
            .order_by("date")
            .last()
        )

        try:
            complexity = metric.metrics["complexity"]
        except (KeyError, AttributeError):
            complexity = 0

        try:
            ref_complexity = ref_metric.metrics["complexity"]
        except (KeyError, AttributeError):
            ref_complexity = 0

        change = self.get_value_change(ref_complexity, complexity)
        return change

    def get_avg_issue_age(self, date_from, date_to):
        kwargs = {
            "project": self,
            "date__gte": date_from,
            "date__lte": date_to,
        }

        age = 0
        metric = Metric.objects.filter(**kwargs).order_by("date").last()
        if metric:
            age = (
                metric.metrics["github_issue_age"]
                if "github_issue_age" in metric.metrics
                else 0
            )

        return age

    def get_avg_pr_age(self, date_from, date_to):
        kwargs = {
            "project": self,
            "date__gte": date_from,
            "date__lte": date_to,
        }

        age = 0
        metric = Metric.objects.filter(**kwargs).order_by("date").last()
        if metric:
            age = (
                metric.metrics["github_pull_requests_cumulative_age"] or 0
                if "github_pull_requests_cumulative_age" in metric.metrics
                else 0 / metric.metrics["github_pull_requests_merged"] or 1
                if "github_pull_requests_merged" in metric.metrics
                and metric.metrics["github_pull_requests_merged"] != 0
                else 1
            )
        age = age / 60 / 60

        return age

    def get_file_complexity_trend(self, path, date_from, date_to):
        """
        Return an array of complexities for the given path over the given time period.

        :param path: The file for which the complexities should be returned.
        :return: Array of integers
        """
        try:
            ref_complexity = (
                Complexity.objects.filter(
                    project=self,
                    file_path=path,
                    timestamp__date__gte=date_from,
                    timestamp__date__lte=date_to,
                )
                .order_by("-timestamp")
                .first()
                .complexity
            )
        except AttributeError:
            ref_complexity = 0

        source_status = self.get_source_status(date=date_to)
        is_file = (
            SourceNode.objects.get(
                source_status=source_status,
                path=os.path.join(self.github_repo_name, path),
            )
            .children.all()
            .count()
            == 0
        )
        complexities = {}
        if is_file:
            for day in date_range(date_from, date_to):
                complexities[day.strftime("%Y-%m-%d")] = ref_complexity

            comps = Complexity.objects.filter(
                project=self,
                file_path=path,
                timestamp__date__gte=date_from,
                timestamp__date__lte=date_to,
            ).order_by("timestamp")

            for comp in comps:
                complexities[comp.timestamp.strftime("%Y-%m-%d")] = comp.complexity
        else:
            comps = Complexity.objects.filter(
                project=self,
                file_path=path,
                timestamp__date__gte=date_from,
                timestamp__date__lte=date_to,
            ).order_by("timestamp")

            for comp in comps:
                key = comp.timestamp.strftime("%Y-%m-%d")
                if key not in complexities.keys():
                    complexities[comp.timestamp.strftime("%Y-%m-%d")] = 0

                complexities[key] = complexities[key] + comp.complexity

        return sorted(complexities.items())

    def get_file_changes_trend(self, path, date_from, date_to):
        """
        Return an array of code change for the given path over the given time period.

        :param path: The file for which the code changes should be returned.
        :return: Array of integers
        """
        changes = {}
        for day in date_range(date_from, date_to):
            changes[day.strftime("%Y-%m-%d")] = 0

        source_status = self.get_source_status(date=date_to)
        is_file = (
            SourceNode.objects.get(
                source_status=source_status,
                path=os.path.join(self.github_repo_name, path),
            )
            .children.all()
            .count()
            == 0
        )
        if is_file:
            raw_changes = (
                CodeChange.objects.filter(
                    project=self,
                    file_path=path,
                    timestamp__date__gte=date_from,
                    timestamp__date__lte=date_to,
                )
                .extra(select={"day": "TO_CHAR(timestamp, 'YYYY-MM-DD')"})
                .values("day")
                .annotate(changes=Count("timestamp"))
            )
        else:
            raw_changes = (
                CodeChange.objects.filter(
                    project=self,
                    file_path__startswith=path,
                    timestamp__date__gte=date_from,
                    timestamp__date__lte=date_to,
                )
                .extra(select={"day": "TO_CHAR(timestamp, 'YYYY-MM-DD')"})
                .values("day")
                .annotate(changes=Count("timestamp"))
            )

        for raw_change in raw_changes:
            changes[raw_change["day"]] = raw_change["changes"]

        return sorted(changes.items())

    def get_file_metrics(self, path):
        path = os.path.join(self.github_repo_name, path)
        node = SourceNode.objects.get(
            source_status=self.current_source_status, path=path
        )
        if node.children.all().count() == 0:
            return node.json_representation
        else:
            return SourceNode.objects.filter(
                source_status=self.current_source_status, path__startswith=path
            )

    def get_file_ownership(self, path):
        file_metrics = self.get_file_metrics(path)
        if type(file_metrics) == dict:
            ownership = file_metrics["ownership"]
        else:
            lines = {}
            for node in file_metrics:
                node_json = node.json_representation["ownership"]
                for node_ownership in node_json:
                    if node_ownership["author"] not in lines.keys():
                        lines[node_ownership["author"]] = 0
                    lines[node_ownership["author"]] = (
                        lines[node_ownership["author"]] + node_ownership["lines"]
                    )

            ownership = [{"author": key, "lines": lines[key]} for key in lines.keys()]

        # only return top 4 and the rest as "others"
        top = ownership[:4]

        others = ownership[6:]
        lines_of_others = sum([x["lines"] for x in others])

        if len(others) > 0:
            top.append(
                {
                    "author": "%s Others" % len(others),
                    "lines": lines_of_others,
                }
            )

        # normalize ownership to percentage values
        sum_values = sum([x["lines"] for x in top])
        for x in top:
            x["lines"] = round(x["lines"] / sum_values * 100)

        return top


class LogEntry(models.Model):
    project = models.ForeignKey(
        "Project",
        on_delete=models.CASCADE,
    )
    timestamp_start = models.DateTimeField()
    timestamp_end = models.DateTimeField(
        null=True,
    )
    message = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.project} {self.message} ({self.timestamp_start} - {self.timestamp_end})"

    class Meta:
        ordering = ["-timestamp_start"]


class Metric(models.Model):
    project = models.ForeignKey(
        "Project",
        on_delete=models.CASCADE,
        related_name="metrics",
    )
    date = models.DateField()
    file_path = models.CharField(max_length=255, blank=True)
    metrics = JSONField(null=True, blank=True)

    class Meta:
        unique_together = (("project", "date"),)


class SourceStatus(models.Model):
    project = models.ForeignKey(
        "Project",
        on_delete=models.CASCADE,
        related_name="source_stati",
    )
    timestamp = models.DateTimeField()
    active = models.BooleanField(default=False)

    @property
    def simple_tree(self):
        def render_tree(node):
            current_node = node.simple_json_representation
            for child in node.get_children():
                current_node["children"].append(render_tree(child))

            return current_node

        root = SourceNode.objects.get(source_status=self, parent__isnull=True)
        return render_tree(root)

    @property
    def tree(self):
        def render_tree(node):
            current_node = node.json_representation
            for child in node.get_children():
                current_node["children"].append(render_tree(child))

            return current_node

        root = SourceNode.objects.get(source_status=self, parent__isnull=True)
        return render_tree(root)

    @property
    def min_changes(self):
        return (
            SourceNode.objects.filter(source_status=self)
            .aggregate(Min("changes"))
            .get("changes__min", 1)
        )

    @property
    def max_changes(self):
        return (
            SourceNode.objects.filter(source_status=self)
            .aggregate(Max("changes"))
            .get("changes__max", 1)
        )

    @property
    def min_complexity(self):
        return (
            SourceNode.objects.filter(source_status=self)
            .aggregate(Min("complexity"))
            .get("complexity__min", 1)
        )

    @property
    def max_complexity(self):
        return (
            SourceNode.objects.filter(source_status=self)
            .aggregate(Max("complexity"))
            .get("complexity__max", 1)
        )

    def __str__(self):
        return f"{self.project} on {self.timestamp}"


class SourceNode(MPTTModel):
    source_status = models.ForeignKey(
        "SourceStatus",
        on_delete=models.CASCADE,
    )

    name = models.CharField(max_length=255)
    parent = TreeForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )

    path = models.CharField(max_length=255, null=False, default="")
    repo_link = models.CharField(max_length=255, null=False, default="")

    complexity = models.PositiveIntegerField(null=False, default=1)
    changes = models.PositiveIntegerField(null=False, default=1)
    ownership = JSONField(null=False, default=list)

    def __str__(self):
        return self.name

    @property
    def is_file(self):
        return self.repo_link != ""

    @property
    def project_path(self):
        return os.sep.join(self.path.split(os.sep)[1:])  # remove first directory

    @property
    def simple_json_representation(self):
        representation = {
            "path": self.project_path,
            "is_file": self.is_file,
            "size": self.complexity,
            "changes": self.changes,
            "children": [],
        }

        return representation

    @property
    def json_representation(self):
        representation = {
            "name": self.name,
            "path": self.project_path,
            "repo_link": self.repo_link,
            "is_file": self.is_file,
            "size": self.complexity,
            "changes": self.changes,
            "ownership": self.ownership,
            "children": [],
        }

        return representation

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        unique_together = [["parent", "name"]]


class Release(models.Model):
    project = models.ForeignKey(
        "Project",
        on_delete=models.CASCADE,
    )
    timestamp = models.DateTimeField()
    type = models.CharField(max_length=20, default="git_tag")
    name = models.CharField(max_length=100)
    url = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.name} ({self.pk})"


class Complexity(models.Model):
    project = models.ForeignKey(
        "core.Project",
        on_delete=models.CASCADE,
    )
    timestamp = models.DateTimeField()
    file_path = models.CharField(max_length=255)
    complexity = models.PositiveIntegerField()
