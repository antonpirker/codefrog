import json
import subprocess
import tempfile

import requests
from django.conf import settings
from django.http import HttpResponse
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
