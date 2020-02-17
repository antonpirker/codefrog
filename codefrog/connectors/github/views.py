import logging

from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.http.response import HttpResponseRedirect
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt

from connectors.github.router import github_hook
from core.models import Project
from core.utils import GitHub
from web.models import Plan
from web.models import UserProfile

logger = logging.getLogger(__name__)


@csrf_exempt
def hook(request):
    logger.debug('########## hook')
    logger.debug('-----------------------------------------------------------')
    logger.debug('request.headers: %s ' % request.headers)
    logger.debug('-----------------------------------------------------------')
    logger.debug('request.body: %s' % request.body)
    logger.debug('-----------------------------------------------------------')

    if 'X-Github-Event' in request.headers:
        msg = github_hook(request)
    else:
        msg = 'Not implemented yet.'

    return HttpResponse(msg)


@csrf_exempt
def setup(request):
    logger.debug('########## setup')
    logger.debug('-----------------------------------------------------------')
    logger.debug('request.headers: %s ' % request.headers)
    logger.debug('-----------------------------------------------------------')
    logger.debug('request.body: %s' % request.body)
    logger.debug('-----------------------------------------------------------')
    # request.GET: <QueryDict: {'installation_id': ['2115097'], 'setup_action': ['install']}>

    # Redirect back to where request came from
    url = request.META['HTTP_REFERER']
    return HttpResponseRedirect(url)


@csrf_exempt
def authorization(request):
    logger.debug('########## authorization')
    logger.debug('-----------------------------------------------------------')
    logger.debug('request.headers: %s ' % request.headers)
    logger.debug('-----------------------------------------------------------')
    logger.debug('request.body: %s' % request.body)
    logger.debug('-----------------------------------------------------------')

    state = request.GET.get('state', None)
    code = request.GET.get('code', None)
    installation_id = request.GET.get('installation_id', None)

    # TODO: compare the state with the state we create in the index page.
    #  (if we did not create a state in the index (the app was installed from github.com) there is no state,
    #  so both must be none

    # get information about the user
    gh = GitHub(code=code, state=state)
    user_data = gh.get_user()
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
        defaults={
            'github_app_installation_refid': installation_id,
            'plan': Plan.objects.get(slug=state),
        }
    )

    login(request, user)

    # import projects of the user
    repositories = gh.get_installation_repositories(installation_id)
    for repository in repositories['repositories']:
        project, created = Project.objects.update_or_create(
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
