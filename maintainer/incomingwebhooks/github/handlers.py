import secrets
from random import randrange

from django.contrib.auth.models import User
from django.urls import reverse

from core.models import Project, UserProfile
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
            slug=repository_data['full_name'].replace('/', '-'),
            name=repository_data['name'],
            git_url=repository_data['clone_url'],
            defaults={
                'private': repository['private'],
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

    # Get the before and after code

    # Calculate complexity before
    # TODO: really check out the source and run calculation
    complexity_before = 100

    # Calculate complexity after
    # TODO: really check out the source and run calculation
    complexity_after = randrange(93, 106)

    # Calculate change
    complexity_change = round((100 / complexity_before) * complexity_after - 100, 1)

    # Tell Github the change complexity and that the check is not completed.
    sunny = '🌞'  # U+1F31E
    party_cloudy = '⛅'  # U+26C5
    cloudy = '☁'  # U+2601
    stormy = '⛈'  # U+26C8
    unknown = ''  # nothing :)

    if complexity_change <= 0:
        icon = sunny
    elif 0 < complexity_change <= 2.5:
        icon = party_cloudy
    elif 2.5 < complexity_change <= 5:
        icon = cloudy
    elif complexity_change > 5:
        icon = stormy
    else:
        icon = unknown

    conclusion = 'neutral' if complexity_change > 0 else 'success'

    title = f'{icon} Complexity: {complexity_change:+.1f}%' if complexity_change > 0 \
        else f'{icon} Complexity: {complexity_change:+.1f}%'
    summary = f"""You have increased your complexity of the system by {complexity_change:+.1f}%.
        This is not a good sign. Maybe see if you can refactor your code
        a little to have less complexity.""" if complexity_change > 0 \
        else f"""You have decreased your complexity of the system by {complexity_change:+.1f}%.
        Well done!"""

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