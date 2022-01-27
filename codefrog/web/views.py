import hashlib
import secrets

import structlog
from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.template.loader import render_to_string
from django.utils import timezone

from core.decorators import only_matching_authenticated_users, add_user_and_project
from web.models import Message
from web.models import Usage

logger = structlog.get_logger(__name__)


def landing(request):
    """
    Main landing page
    """
    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project_id=None,
        timestamp=timezone.now(),
        action="landing_page.view",
    )

    context = {}
    html = render_to_string("landing.html", context=context, request=request)

    return HttpResponse(html)


def connect_github(request):
    """
    Connect Codefrog to your GitHub Account
    """
    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project_id=None,
        timestamp=timezone.now(),
        action="connect_github_page.view",
    )

    plan = request.GET.get("plan", "minimum")

    bytes = b"%s%s" % (settings.SECRET_KEY.encode("utf8"), plan.encode("utf8"))
    hash = "hash_%s" % hashlib.sha224(bytes).hexdigest()

    context = {
        "github_state": secrets.token_urlsafe(50),
        "plan": plan,
        "hash": hash,
    }
    html = render_to_string("connect_github.html", context=context, request=request)

    return HttpResponse(html)


def pricing(request):
    """
    List pricing model
    """
    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project_id=None,
        timestamp=timezone.now(),
        action="pricing_page.view",
    )

    context = {
        "something": 1 / 0,
        "github_state": secrets.token_urlsafe(50),
    }

    signing = request.GET.get("signing", False)

    if signing:
        context["signin"] = True
        context["headline"] = "No matching account found!"
        context[
            "message"
        ] = """
            You do not yet have an Codefrog account matching your GitHub account.<br/>
            Please choose an account type below and start your free trial:
        """

    html = render_to_string("pricing.html", context=context, request=request)
    return HttpResponse(html)


@only_matching_authenticated_users
def user_settings(request, username):
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        raise Http404("User does not exist")

    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project=None,
        timestamp=timezone.now(),
        action="user_settings.view",
    )

    context = {
        "user": user,
        "projects": user.projects.all().order_by("name"),
    }
    html = render_to_string("settings/user.html", context=context)
    return HttpResponse(html)


@only_matching_authenticated_users
@add_user_and_project
def project_settings(request, username, project_slug, user, project):
    Usage.objects.create(
        user=request.user if request.user.is_authenticated else None,
        project=None,
        timestamp=timezone.now(),
        action="project_settings.view",
    )

    context = {
        "user": request.user,
        "project": project,
    }
    html = render_to_string("settings/project.html", context=context)
    return HttpResponse(html)


def feedback(request):
    url = request.META.get("HTTP_REFERER", None)

    if request.method == "POST":
        message = request.POST.get("message", None)
        if message:
            Message.objects.create(
                timestamp=timezone.now(),
                message=message,
                user=request.user if request.user.is_authenticated else None,
                url=url,
            )

    return HttpResponseRedirect(url)
