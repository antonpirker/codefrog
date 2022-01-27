import secrets

import structlog
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify

from connectors.github.utils import create_check_run, get_access_token
from core.models import Project
from core.utils import GitHub
from pullrequestbot import checks
from web.models import UserProfile

logger = structlog.get_logger(__name__)


def installation__created(payload, request=None):
    logger.info("### INSTALLATION / CREATED")
    installation_id = payload["installation"]["id"]

    # create a user in our database
    user, user_created = User.objects.update_or_create(
        username=payload["sender"]["login"],
        is_staff=False,
        is_active=True,
        is_superuser=False,
        defaults={
            "password": secrets.token_urlsafe(90),
        },
    )
    UserProfile.objects.update_or_create(
        user=user,
        defaults={
            "github_app_installation_refid": installation_id,
        },
    )
    logger.info(f"- User {user} (with user profile) created")

    # add all repositories to the user
    gh = GitHub(installation_id=installation_id)
    for repository in payload["repositories"]:
        repository_data = gh.get_repository(repository["full_name"])
        project, project_created = Project.objects.update_or_create(
            user=user,
            source="github",
            slug=slugify(repository_data["full_name"].replace("/", "-")),
            name=repository_data["name"],
            git_url=repository_data["clone_url"],
            defaults={
                "private": repository_data["private"],
            },
        )

        if project_created:
            logger.info(f"- Project {project} created")
        else:
            logger.info(f"- Project {project} updated")

        project.external_services = {"github": {"repository_id": repository["id"]}}
        project.save()

    logger.info("### FINISHED INSTALLATION / CREATED")


def installation__deleted(payload, request=None):
    logger.info("### INSTALLATION / DELETED")
    installation_id = payload["installation"]["id"]

    # set all projects that belong to the user with the given installation to inactive
    user = User.objects.get(profile__github_app_installation_refid=installation_id)
    Project.objects.filter(user=user).update(active=False)
    logger.info(f"- Set all projects of user {user} to inactive.")

    # delete all git repos on the local disk
    for project in Project.objects.filter(user=user):
        project.delete_repo_dir()
    logger.info(f"- Deleted all source code from all projects of user {user}.")

    # delete github_app_installation_refid id from userprofile
    user.profile.github_app_installation_refid = None
    user.profile.save()
    logger.info(f"- Removed link to GitHub app installation from user {user}.")

    logger.info("### FINISHED INSTALLATION / DELETED")


def installation__suspend(payload, request=None):
    logger.info("### INSTALLATION / SUSPEND")
    # do nothing
    logger.info("### FINISHED INSTALLATION / SUSPEND")


def installation__unsuspend(payload, request=None):
    logger.info("### INSTALLATION / UNSUSPEND")
    # do nothing
    logger.info("### FINISHED INSTALLATION / UNSUSPEND")


def installation__new_permissions_accepted(payload, request=None):
    logger.info("### INSTALLATION / NEW PERMISSIONS ACCEPTED")
    # do nothing
    logger.info("### FINISHED INSTALLATION / NEW PERMISSIONS ACCEPTED")


def check_suite__requested(payload, request=None):
    """
    Performs the pull request bot check.

    :param payload:
    :param request:
    :return:
    """
    logger.info("Starting check_suite__requested")
    event = "check_suite"
    action = "requested"

    installation_id = payload["installation"]["id"]
    repository_full_name = payload["repository"]["full_name"]
    repository_github_id = payload["repository"]["id"]
    commit_sha_before = payload[event]["before"]
    commit_sha_after = payload[event]["after"]

    try:
        project = checks.get_project_matching_github_hook(payload)
    except Project.DoesNotExist:
        project = None

    if not project:
        logger.warning(
            "Project not found for Github web hook for repo %s(%s)",
            repository_full_name,
            repository_github_id,
        )
        return

    installation_access_token = get_access_token(installation_id)

    check_run_name = "Complexity Check"

    # Tell Github we queued our check
    check_run_payload = {
        "name": check_run_name,
        "head_sha": commit_sha_after,
        "status": "queued",
    }
    create_check_run(repository_full_name, installation_access_token, check_run_payload)
    logger.info('Set check to "queued" in Github')

    # Tell Github we started the check
    check_run_payload = {
        "name": check_run_name,
        "head_sha": commit_sha_after,
        "status": "in_progress",
    }
    create_check_run(repository_full_name, installation_access_token, check_run_payload)
    logger.info('Set check to "in progress" in Github')

    # Perform check
    logger.info("Performing complexity check")
    details_url = request.build_absolute_uri(
        reverse("project-detail", kwargs={"slug": project.slug})
    )
    output = checks.perform_complexity_check(
        project=project,
        commit_sha_before=commit_sha_before,
        commit_sha_after=commit_sha_after,
        project_url=details_url,
    )
    logger.info("Finished performing complexity check")

    # Set check to completed and display result
    check_run_payload = {
        "name": check_run_name,
        "status": "completed",
        "head_sha": commit_sha_after,
        "details_url": details_url,
        "conclusion": output["conclusion"],
        "output": {
            "title": output["title"],
            "summary": output["summary"],
        },
    }
    out = create_check_run(
        repository_full_name, installation_access_token, check_run_payload
    )
    logger.info('Told Github the result of the check and set it to "completed".')

    logger.info("Finished check_suite__requested")
    return out
