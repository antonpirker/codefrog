import secrets

from django.conf import settings as django_settings


def settings(request):
    github_oauth_url = "https://github.com/login/oauth/authorize"
    random_string = secrets.token_urlsafe(90)
    github_sign_in_url = (
        f"{github_oauth_url}?"
        f"client_id={django_settings.GITHUB_APP_CLIENT_ID}&"
        f"redirect_uri={django_settings.GITHUB_AUTH_REDIRECT_URI}&"
        f"state={random_string}"
    )

    return {
        "LIVE_SYSTEM": django_settings.LIVE_SYSTEM,
        "github_sign_in_url": github_sign_in_url,
    }
