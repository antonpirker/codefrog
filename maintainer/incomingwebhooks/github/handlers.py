from random import randrange

from incomingwebhooks.github.utils import create_check_run, get_access_token


def check_suite__requested(payload):
    event = 'check_suite'
    action = 'requested'

    repository_full_name = payload['repository']['full_name']
    commit_sha_before = payload[event]['before']
    commit_sha_after = payload[event]['after']

    installation_access_token = get_access_token(
        payload['installation']['id'],
        payload['repository']['id'],
    )

    # Tell Github we queued our check
    payload = {
        'name': 'Complexity',
        'head_sha': commit_sha_after,
        'status': 'queued',
    }
    out = create_check_run(repository_full_name, installation_access_token, payload)

    # Actually start the check
    payload = {
        'name': 'Complexity',
        'head_sha': commit_sha_after,
        'status': 'in_progress',
    }
    out = create_check_run(repository_full_name, installation_access_token, payload)

    # Get the before and after code

    # Calculate complexity before
    # TODO: really check out the source and run calculation
    complexity_before = 100

    # Calculate complexity after
    # TODO: really check out the source and run calculation
    complexity_after = randrange(93, 106)

    # Calculate change
    complexity_change = round((100/complexity_before) * complexity_after - 100, 1)

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

    payload = {
        'name': 'Complexity',
        'head_sha': commit_sha_after,
        'status': 'completed',
        'conclusion': conclusion,
        'output': {
            'title': title,
            'summary': summary,
        }
    }
    out = create_check_run(repository_full_name, installation_access_token, payload)
    return out
