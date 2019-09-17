import jwt
import time
import datetime
import json
import subprocess
import tempfile

import requests
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from git import Repo


@csrf_exempt
def gitlab_merge_request(request):
    # receive web hook
    data = json.loads(request.body)
    project_id = data['project']['id']
    merge_request_id = data['object_attributes']['iid']

    # get source
    source_repo_url = data['object_attributes']['target']['git_ssh_url']
    source_branch = data['object_attributes']['target_branch']
    source_repo_dir = tempfile.mkdtemp()
    repo = Repo.clone_from(source_repo_url, source_repo_dir)
    repo.git.checkout(source_branch)

    # calculate metrics for source
    source_complexity_command = 'lizard {} --csv | cut --delimiter=, --fields=2 | paste -sd+ - | bc'.format(source_repo_dir)
    source_complexity = float(subprocess.run([source_complexity_command, ], capture_output=True, shell=True).stdout)

    # get target
    target_repo_url = data['object_attributes']['source']['git_ssh_url']
    target_branch = data['object_attributes']['source_branch']
    target_repo_dir = tempfile.mkdtemp()
    repo = Repo.clone_from(target_repo_url, target_repo_dir)
    repo.git.checkout(target_branch)

    # calculate metrics of target
    target_complexity_command = 'lizard {} --csv | cut --delimiter=, --fields=2 | paste -sd+ - | bc'.format(target_repo_dir)
    target_complexity = float(subprocess.run([target_complexity_command, ], capture_output=True, shell=True).stdout)

    # calculate delta
    complexity_delta = 100/source_complexity * target_complexity - 100

    # post delta to gitlab
    api_url = '{}/projects/{}/merge_requests/{}/notes'.format(
        settings.GITLAB_API_BASE_URL, project_id, merge_request_id)
    payload = {
        'body': (
            f'This merge requests introduces those changes: \n',
            f'    Change in code complexity: {complexity_delta:.2f}%',
        )
    }
    requests.post(api_url, data=payload, headers=settings.GITLAB_API_DEFAULT_HEADERS)

    return HttpResponse('')


@csrf_exempt
def github_apps_webhook(request):
    event = request.headers['X-Github-Event']
    payload = json.loads(request.body)
    repository_full_name = payload['repository']['full_name']
    action = payload['action']

    import ipdb; ipdb.set_trace()
    if event == 'check_suite':
        if action == 'requested':
            commit_sha_before = payload[event]['before']
            commit_sha_after = payload[event]['after']

            # Generate the JWT
            private_key = settings.GITHUB_PRIVATE_KEY.decode("utf-8")
            current_time = int(time.time())

            jwt_payload = {
                # issued at time
                'iat': current_time,
                # JWT expiration time (10 minute maximum)
                'exp': current_time + (10 * 60),
                # GitHub App's identifier
                'iss': settings.GITHUB_APP_IDENTIFIER,
            }

            token = jwt.encode(jwt_payload, private_key, algorithm='RS256').decode("utf-8")

            headers = {
                'Accept': 'application/vnd.github.machine-man-preview+json',
                'Authorization': 'Bearer %s' % token,
            }

            installation_id = payload['installation']['id']
            url = f'/app/installations/{installation_id}/access_tokens'
            api_base_url = 'https://api.github.com'
            api_url = f'{api_base_url}{url}'

            api_payload = {
                "repository_ids": [
                    payload['repository']['id']
                ],
                "permissions": {
                    "checks": "write",
                    "contents": "read"
                }
            }

            out = requests.post(api_url, data=json.dumps(api_payload), headers=headers)
            out = json.loads(out.content)

            installation_access_token = out['token']

            # create check run
            api_payload = {
                'name': 'check_complexity',
                'head_sha': commit_sha_after,
                'status': 'completed',
                #'details_url': 'https://codefrog.io/projects/atom',
                #'started_at': '2019-10-10T14:33:54Z',
                #'completed_at': '2019-10-10T14:34:49Z',
                'conclusion': 'neutral',  # success, failure, neutral, cancelled, timed_out, or action_required
                'output': {
                    'title': 'Complexity increased',
                    'summary': 'You have increased your complexity of the system by 11%. This is not a good sign. Maybe see if you can refactor your code a little to have less complexity.',
                }
            }

            url = f'/repos/{repository_full_name}/check-runs'
            api_base_url = 'https://api.github.com'
            api_url = f'{api_base_url}{url}'

            headers = {
                'Accept': 'application/vnd.github.antiope-preview+json',
                'Authorization': 'token %s' % installation_access_token,
            }
            out = requests.post(api_url, data=json.dumps(api_payload), headers=headers)


    elif event == 'check_run':
        # manually requests a new run.
        pass

    return HttpResponse('')
