import datetime
import secrets

from django.http import HttpResponse
from django.template.loader import render_to_string

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
    html = render_to_string('website/landing.html', context=context, request=request)

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

    context = {
        'github_state': secrets.token_urlsafe(50),
        'plan': plan,
    }
    html = render_to_string('website/connect_github.html', context=context, request=request)

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
    html = render_to_string('website/pricing.html', context=context, request=request)

    return HttpResponse(html)

