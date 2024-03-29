import datetime

import structlog
from celery import shared_task
from django.utils import timezone

from core.models import Project, Release
from core.utils import GitHub, log, make_one
from engine.models import Issue, OpenIssue, PullRequest
from web.models import UserProfile

logger = structlog.get_logger(__name__)


@shared_task
def import_issues(project_id, start_date=None, *args, **kwargs):
    logger.info("Project(%s): Starting import_issues. (%s)", project_id, start_date)
    project_id = make_one(project_id)
    log(project_id, "Importing Github issues", "start")

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning("Project with id %s not found. ", project_id)
        logger.info("Project(%s): Finished (aborted) import_issues.", project_id)
        return

    try:
        installation_id = project.user.profile.github_app_installation_refid
    except UserProfile.DoesNotExist:
        installation_id = None

    gh = GitHub(installation_id=installation_id)

    issues = gh.get_issues(
        repo_owner=project.github_repo_owner,
        repo_name=project.github_repo_name,
        start_date=start_date,
    )

    for issue in issues:
        is_pull_request = "pull_request" in issue
        if not is_pull_request:
            try:
                labels = [label["name"] for label in issue["labels"]]
            except TypeError:
                labels = []

            opened_at = datetime.datetime.strptime(
                issue["created_at"],
                "%Y-%m-%dT%H:%M:%SZ",
            ).replace(tzinfo=timezone.utc)

            if issue["closed_at"]:
                closed_at = datetime.datetime.strptime(
                    issue["closed_at"],
                    "%Y-%m-%dT%H:%M:%SZ",
                ).replace(tzinfo=timezone.utc)
            else:
                closed_at = None

            raw_issue, created = Issue.objects.update_or_create(
                project_id=project_id,
                issue_refid=issue["number"],
                opened_at=opened_at,
                defaults={
                    "closed_at": closed_at,
                    "labels": labels,
                },
            )
            logger.debug(f"{raw_issue}: created: {created}")

    logger.info(
        "Project(%s): Finished import_issues. (%s)",
        project_id,
        start_date,
    )
    log(project_id, "Importing Github issues", "stop")

    return project_id


@shared_task
def import_open_issues(project_id, *args, **kwargs):
    logger.info("Project(%s): Starting import_open_issues.", project_id)
    project_id = make_one(project_id)
    log(project_id, "Import of currently open GitHub issues", "start")

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning("Project with id %s not found. ", project_id)
        logger.info("Project(%s): Finished (aborted) import_open_issues.", project_id)
        return

    try:
        installation_id = project.user.profile.github_app_installation_refid
    except UserProfile.DoesNotExist:
        installation_id = None

    gh = GitHub(installation_id=installation_id)

    # Delete all old open issues of today
    OpenIssue.objects.filter(
        project_id=project_id,
        query_time__date=timezone.now().date(),
    ).delete()

    issues = gh.get_open_issues(
        repo_owner=project.github_repo_owner,
        repo_name=project.github_repo_name,
    )

    for issue in issues:
        is_pull_request = "pull_request" in issue
        if not is_pull_request:
            try:
                labels = [label["name"] for label in issue["labels"]]
            except TypeError:
                labels = []

            OpenIssue.objects.create(
                project_id=project_id,
                issue_refid=issue["number"],
                query_time=timezone.now(),
                labels=labels,
            )

    logger.info(
        "Project(%s): Finished import_open_issues.",
        project_id,
    )
    log(project_id, "Import of currently open GitHub issues", "stop")

    return project_id


@shared_task
def import_releases(project_id, *args, **kwargs):
    logger.info("Project(%s): Starting import_releases.", project_id)
    project_id = make_one(project_id)
    log(project_id, "Importing Github releases", "start")

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning("Project with id %s not found. ", project_id)
        logger.info("Project(%s): Finished (aborted) import_releases.", project_id)
        return

    try:
        installation_id = project.user.profile.github_app_installation_refid
    except UserProfile.DoesNotExist:
        installation_id = None

    gh = GitHub(installation_id=installation_id)

    releases = gh.get_releases(
        repo_owner=project.github_repo_owner,
        repo_name=project.github_repo_name,
    )

    for release in releases:
        try:
            release_name = release["tag_name"]
            release_date = release["published_at"]
            release_url = release["html_url"]
        except TypeError:
            logger.warn("Could not get tag_name!")
            logger.warn("release: %s" % release)

        logger.debug(
            "Project(%s): Github Release %s %s.",
            project_id,
            release_name,
            release_date,
        )
        Release.objects.update_or_create(
            project_id=project_id,
            timestamp=release_date,
            type="github_release",
            name=release_name,
            url=release_url,
        )

    logger.info(
        "Project(%s): Finished import_releases.",
        project_id,
    )
    log(project_id, "Importing Github releases", "stop")

    return project_id


@shared_task
def import_pull_requests(project_id, *args, **kwargs):
    logger.info("Project(%s): Starting import_pull_requests.", project_id)
    project_id = make_one(project_id)
    log(project_id, "Importing Github pull requests", "start")

    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        logger.warning("Project with id %s not found. ", project_id)
        logger.info("Project(%s): Finished (aborted) import_pull_requests.", project_id)
        return

    try:
        installation_id = project.user.profile.github_app_installation_refid
    except UserProfile.DoesNotExist:
        installation_id = None

    gh = GitHub(installation_id=installation_id)

    pull_requests = gh.get_pull_requests(
        repo_owner=project.github_repo_owner,
        repo_name=project.github_repo_name,
    )

    for pull_request in pull_requests:
        is_merge_into_default_branch = project.git_branch == pull_request["base"]["ref"]
        if not is_merge_into_default_branch:
            continue

        opened_at = datetime.datetime.strptime(
            pull_request["created_at"],
            "%Y-%m-%dT%H:%M:%SZ",
        ).replace(tzinfo=timezone.utc)

        if pull_request["merged_at"]:
            merged_at = datetime.datetime.strptime(
                pull_request["merged_at"],
                "%Y-%m-%dT%H:%M:%SZ",
            ).replace(tzinfo=timezone.utc)
        else:
            merged_at = None

        if merged_at:
            age = (merged_at - opened_at).seconds
        else:
            age = None

        try:
            labels = [label["name"] for label in pull_request["labels"]]
        except TypeError:
            labels = []

        raw_pull_request, created = PullRequest.objects.update_or_create(
            project_id=project_id,
            pull_request_refid=pull_request["number"],
            opened_at=opened_at,
            defaults={
                "merged_at": merged_at,
                "age": age,
                "labels": labels,
            },
        )
        logger.debug(f"{raw_pull_request}: created: {created}")

    logger.info(
        "Project(%s): Finished import_pull_requests.",
        project_id,
    )
    log(project_id, "Importing Github pull requests", "stop")

    return project_id
