import shutil
import os
import secrets
from random import randrange

from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify
from git import Repo

from core.models import Project, UserProfile
from core.utils import get_path_complexity
from incomingwebhooks.github.utils import create_check_run, get_access_token, \
    get_repository


def installation__created(payload, request=None):
    print("### INSTALLATION / CREATED")
    # create a user in our database
    user, created = User.objects.get_or_create(
        username=payload['sender']['login'],
        is_staff=False,
        is_active=True,
        is_superuser=False,
        defaults={
            'password': secrets.token_urlsafe(90),
        },
    )
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'github_app_installation_refid': payload['installation']['id'],
        },
    )

    # add all repositories to the user
    for repository in payload['repositories']:
        repository_data = get_repository(
            payload['installation']['id'],
            repository['full_name'],
        )

        project, created = Project.objects.get_or_create(
            user=user,
            source='github',
            slug=slugify(repository_data['full_name'].replace('/', '-')),
            name=repository_data['name'],
            git_url=repository_data['clone_url'],
            defaults={
                'private': repository_data['private'],
            },
        )

        if created:
            project.external_services = {
                'github': {
                    'repository_id': repository['id']
                }
            }
            project.save()


def integration_installation__created(payload, request=None):
    # deprecated event. is succeeded by installation_created
    pass


def installation__deleted(payload, request=None):
    print("### INSTALLATION / DELETED")


def check_suite__requested(payload, request=None):
    event = 'check_suite'
    action = 'requested'

    repository_full_name = payload['repository']['full_name']
    commit_sha_before = payload[event]['before']
    commit_sha_after = payload[event]['after']

    installation_access_token = get_access_token(
        payload['installation']['id'],
    )

    # Tell Github we queued our check
    check_run_payload = {
        'name': 'Complexity',
        'head_sha': commit_sha_after,
        'status': 'queued',
    }
    out = create_check_run(repository_full_name, installation_access_token, check_run_payload)

    # Actually start the check
    check_run_payload = {
        'name': 'Complexity',
        'head_sha': commit_sha_after,
        'status': 'in_progress',
    }
    out = create_check_run(repository_full_name, installation_access_token, check_run_payload)

    # Get the source code
    git_url = f'https://x-access-token:{installation_access_token}@github.com/{repository_full_name}.git'
    repo_dir = os.path.join(settings.GIT_REPO_DIR, repository_full_name)

    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)
    if not os.path.exists(repo_dir):
        os.makedirs(repo_dir)

    repo = Repo.clone_from(git_url, repo_dir)

    # Calculate complexity before
    repo.git.reset('--hard', commit_sha_before)
    complexity_before = get_path_complexity(repo_dir)

    # Calculate complexity after
    repo.git.reset('--hard', commit_sha_after)
    complexity_after = get_path_complexity(repo_dir)

    # Calculate change
    complexity_change = round((100 / complexity_before) * complexity_after - 100, 1)

    # Tell Github the change complexity and that the check is now completed.
    sunny = '🌞'  # U+1F31E
    party_cloudy = '⛅'  # U+26C5
    cloudy = '☁'  # U+2601
    stormy = '⛈'  # U+26C8
    unknown = ''  # nothing :)

    if complexity_change <= 0:
        icon = sunny
        summary = f"""You have decreased your complexity of the system by {complexity_change:+.1f}%.
        Well done! You are on the right tracks to make your project more maintainable!"""
        conclusion = 'success'

    elif 0 < complexity_change <= 2.5:
        icon = party_cloudy
        summary = f"""You have increased your complexity of the system by {complexity_change:+.1f}%.
        This is OK."""
        conclusion = 'neutral'

    elif 2.5 < complexity_change <= 5:
        icon = cloudy
        summary = f"""You have increased your complexity of the system by {complexity_change:+.1f}%.
        This is OK if you implement some new features. Just make sure, that you keep an eye on the overall complexity."""
        conclusion = 'neutral'

    elif complexity_change > 5:
        icon = stormy
        summary = f"""You have increased your complexity of the system by {complexity_change:+.1f}%.
        This is not a good sign. Maybe see if you can refactor your code
        a little to have less complexity."""
        conclusion = 'neutral'

    else:
        icon = unknown
        summary = f"""I do not know the complexity in your system has changed. Strange thing..."""
        conclusion = 'neutral'

    title = f'{icon} Complexity: {complexity_change:+.1f}%'

    project = Project.objects.get(external_services__github__repository_id=payload['repository']['id'])
    details_url = request.build_absolute_uri(reverse('project-detail', kwargs={'slug': project.slug}))

    check_run_payload = {
        'name': 'Complexity',
        'head_sha': commit_sha_after,
        'status': 'completed',
        'details_url': details_url,
        'conclusion': conclusion,
        'output': {
            'title': title,
            'summary': summary,
        }
    }
    out = create_check_run(repository_full_name, installation_access_token, check_run_payload)
    return out
