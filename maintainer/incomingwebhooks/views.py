import json
import subprocess
import tempfile

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.http import HttpResponse
from django.http.response import HttpResponseRedirect
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from git import Repo

from core.models import Project, UserProfile
from incomingwebhooks.github.router import github_hook
from incomingwebhooks.github.utils import get_user_access_token, get_user, \
    get_installations, get_installation_repositories


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
def hook(request):
    print('########## hook')
    print('-----------------------------------------------------------')
    print('request.headers: %s ' % request.headers)
    print('-----------------------------------------------------------')
    print('request.body: %s' % request.body)
    print('-----------------------------------------------------------')

    if 'X-Github-Event' in request.headers:
        msg = github_hook(request)
    else:
        msg = 'Not implemented yet.'

    return HttpResponse(msg)


@csrf_exempt
def authorization(request):
    print('########## authorization')
    print('-----------------------------------------------------------')
    print('request.headers: %s ' % request.headers)
    print('-----------------------------------------------------------')
    print('request.body: %s' % request.body)
    print('-----------------------------------------------------------')

    state = request.GET.get('state', None)
    code = request.GET.get('code', None)

    # TODO: compare the state with the state we create in the index page.
    #  (if we did not create a state in the index (the app was installed from github.com) there is no state,
    #  so both must be none

    # get information about the user
    access_token = get_user_access_token(code, state)
    user_data = get_user(access_token)
    username = user_data['login']
    email = user_data['email'] or ''

    user, created = User.objects.update_or_create(
        username=username,
        defaults={
            'email': email,
        }
    )
    user_profile, created = UserProfile.objects.update_or_create(
        user=user,
    )

    login(request, user)

    # import projects of the user
    installations = get_installations(access_token)
    print('-----------------------------------------------------------')
    print('installations: %s' % installations)
    print('-----------------------------------------------------------')
    for installation in installations['installations']:
        installation_id = installation['id']
        print('-----------------------------------------------------------')
        print('installation_id: %s' % installation_id)
        print('-----------------------------------------------------------')

        user_profile, created = UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'github_app_installation_refid': installation_id,
            }
        )
        repositories = get_installation_repositories(access_token, installation_id)
        for repository in repositories['repositories']:
            project, created = Project.objects.get_or_create(
                user=user,
                source='github',
                slug=slugify(repository['full_name'].replace('/', '-')),
                name=repository['name'],
                git_url=repository['clone_url'],
                defaults={
                    'private': repository['private'],
                },
            )

    return HttpResponseRedirect(reverse('index'))


@csrf_exempt
def setup(request):
    print('########## setup')
    print('-----------------------------------------------------------')
    print('request.headers: %s ' % request.headers)
    print('-----------------------------------------------------------')
    print('request.body: %s' % request.body)
    print('-----------------------------------------------------------')
    # request.GET: <QueryDict: {'installation_id': ['2115097'], 'setup_action': ['install']}>

    # Redirect back to where request came from
    url = request.META['HTTP_REFERER']
    return HttpResponseRedirect(url)
