import datetime
import hashlib
import secrets

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse, Http404
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils import timezone

from core.decorators import only_matching_authenticated_users, add_user_and_project
from web.models import Message
from web.models import Usage


def landing(request):
    """
    Main landing page
    """
    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project_id=None,
        timestamp=datetime.datetime.utcnow(),
        action='landing_page.view',
    )

    context = {}
    html = render_to_string('landing.html', context=context, request=request)

    return HttpResponse(html)


def connect_github(request):
    """
    Connect Codefrog to your GitHub Account
    """
    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project_id=None,
        timestamp=datetime.datetime.utcnow(),
        action='connect_github_page.view',
    )

    plan = request.GET.get('plan', 'free')

    bytes = b'%s%s' % (settings.SECRET_KEY.encode('utf8'), plan.encode('utf8'))
    hash = 'hash_%s' % hashlib.sha224(bytes).hexdigest()

    context = {
        'github_state': secrets.token_urlsafe(50),
        'plan': plan,
        'hash': hash,
    }
    html = render_to_string('connect_github.html', context=context, request=request)

    return HttpResponse(html)


def pricing(request):
    """
    List pricing model
    """
    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project_id=None,
        timestamp=datetime.datetime.utcnow(),
        action='pricing_page.view',
    )

    context = {
        'github_state': secrets.token_urlsafe(50),
    }
    html = render_to_string('pricing.html', context=context, request=request)

    return HttpResponse(html)


@only_matching_authenticated_users
def user_settings(request, username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        raise Http404('User does not exist')

    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project=None,
        timestamp=datetime.datetime.utcnow(),
        action='user_settings.view',
    )

    context = {
        'user': user,
        'projects': user.projects.all().order_by('name'),
    }
    html = render_to_string('settings/user.html', context=context)
    return HttpResponse(html)


@only_matching_authenticated_users
@add_user_and_project
def project_settings(request, username, project_slug, user, project):
    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project=None,
        timestamp=datetime.datetime.utcnow(),
        action='project_settings.view',
    )

    context = {
        'user': request.user,
        'project': project,
    }
    html = render_to_string('settings/project.html', context=context)
    return HttpResponse(html)


def feedback(request):
    url = request.META.get('HTTP_REFERER', None)

    if request.method == 'POST':
        message = request.POST.get('message', None)
        if message:
            Message.objects.create(
                timestamp=timezone.now(),
                message=message,
                user=request.user if request.user.is_authenticated else None,
                url=url,
            )

    return HttpResponseRedirect(url)
