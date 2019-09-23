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

    # create check run
    payload = {
        'name': 'Complexity1',
        'head_sha': commit_sha_after,
        'status': 'completed',
        'details_url': 'https://codefrog.io/projects/atom',
        'started_at': '2019-10-10T14:33:54Z',
        'completed_at': '2019-10-10T14:34:49Z',
        'conclusion': 'neutral',  # success, failure, neutral, cancelled, timed_out, or action_required
        'output': {
            'title': 'Complexity increased by 50%',
            'summary': 'You have increased your complexity of the system by 11%. This is not a good sign. Maybe see if you can refactor your code a little to have less complexity.',
        }
    }
    create_check_run(repository_full_name, installation_access_token, payload)

    payload = {
        'name': 'Complexity2',
        'head_sha': commit_sha_after,
        'status': 'completed',
        'conclusion': 'success',  # success, failure, neutral, cancelled, timed_out, or action_required
        'output': {
            'title': 'Complexity increased',
            'summary': 'You have increased your complexity of the system by 11%. This is not a good sign. Maybe see if you can refactor your code a little to have less complexity.',
        }
    }
    create_check_run(repository_full_name, installation_access_token, payload)

    payload = {
        'name': 'Complexity3',
        'head_sha': commit_sha_after,
        'status': 'completed',
        'conclusion': 'failure',  # success, failure, neutral, cancelled, timed_out, or action_required
        'output': {
            'title': 'Complexity increased',
            'summary': 'You have increased your complexity of the system by 11%. This is not a good sign. Maybe see if you can refactor your code a little to have less complexity.',
        }
    }
    create_check_run(repository_full_name, installation_access_token, payload)

    payload = {
        'name': 'Complexity4',
        'head_sha': commit_sha_after,
        'status': 'completed',
        'conclusion': 'cancelled',  # success, failure, neutral, cancelled, timed_out, or action_required
        'output': {
            'title': 'Complexity increased',
            'summary': 'You have increased your complexity of the system by 11%. This is not a good sign. Maybe see if you can refactor your code a little to have less complexity.',
        }
    }
    create_check_run(repository_full_name, installation_access_token, payload)

    payload = {
        'name': 'Complexity5',
        'head_sha': commit_sha_after,
        'status': 'completed',
        'conclusion': 'timed_out',  # success, failure, neutral, cancelled, timed_out, or action_required
        'output': {
            'title': 'Complexity increased',
            'summary': 'You have increased your complexity of the system by 11%. This is not a good sign. Maybe see if you can refactor your code a little to have less complexity.',
        }
    }
    create_check_run(repository_full_name, installation_access_token, payload)

    payload = {
        'name': 'Complexity6',
        'head_sha': commit_sha_after,
        'status': 'completed',
        'conclusion': 'action_required',  # success, failure, neutral, cancelled, timed_out, or action_required
        'output': {
            'title': 'Complexity increased',
            'summary': 'You have increased your complexity of the system by 11%. This is not a good sign. Maybe see if you can refactor your code a little to have less complexity.',
        }
    }
    create_check_run(repository_full_name, installation_access_token, payload)

    payload = {
        'name': 'Complexity7',
        'head_sha': commit_sha_after,
        'status': 'queued',
        'conclusion': 'action_required',  # success, failure, neutral, cancelled, timed_out, or action_required
        'output': {
            'title': 'Complexity queued',
            'summary': 'You have increased your complexity of the system by 11%. This is not a good sign. Maybe see if you can refactor your code a little to have less complexity.',
        }
    }
    create_check_run(repository_full_name, installation_access_token, payload)

    payload = {
        'name': 'Complexity8',
        'head_sha': commit_sha_after,
        'status': 'in_progress',
        'conclusion': 'action_required',  # success, failure, neutral, cancelled, timed_out, or action_required
        'output': {
            'title': '🌩🌩🌩🌩🌩🌞 🌤 🌥 🌧 🌩 😃 🙂 😐 😟 😭 Complexity queued',
            'summary': 'You have increased your complexity of the system by 11%. This is not a good sign. Maybe see if you can refactor your code a little to have less complexity.',
        }
    }
    create_check_run(repository_full_name, installation_access_token, payload)


