import hashlib
import hmac
import json
import time

import jwt
import requests
from django.conf import settings
from django.http import Http404
from django.utils.crypto import constant_time_compare
from urllib.parse import parse_qs


def create_jwt():
    """
    Generate a JSON web token (JWT)
    """
    private_key = settings.GITHUB_PRIVATE_KEY.decode("utf-8")
    current_time = int(time.time())

    payload = {
        "iat": current_time,  # issued at time
        "exp": current_time + (10 * 60),  # JWT expiration time (10 minute maximum)
        "iss": settings.GITHUB_APP_IDENTIFIER,  # GitHub App's identifier
    }

    token = jwt.encode(payload, private_key, algorithm="RS256").decode("utf-8")
    return token


def get_access_token(installation_id):
    """
    Authenticate as a Github App and get an installation access token.
    """
    headers = {
        "Accept": "application/vnd.github.machine-man-preview+json",
        "Authorization": "Bearer %s" % create_jwt(),
    }

    url = f"/app/installations/{installation_id}/access_tokens"
    api_base_url = "https://api.github.com"
    api_url = f"{api_base_url}{url}"

    out = requests.post(api_url, headers=headers)
    out = json.loads(out.content)
    token = out["token"]
    return token


def get_user_access_token(code, state):
    api_url = f"https://github.com/login/oauth/access_token"

    payload = {
        "client_id": settings.GITHUB_APP_CLIENT_ID,
        "client_secret": settings.GITHUB_APP_CLIENT_SECRET,
        "redirect_url": settings.GITHUB_AUTH_REDIRECT_URI,
        "code": code,
        "state": state,
    }

    out = requests.post(api_url, data=payload)
    data = parse_qs(out.content.decode())
    access_token = data["access_token"][0]

    return access_token


def get_app_installations():
    headers = {
        "Accept": "application/vnd.github.machine-man-preview+json",
        "Authorization": "Bearer %s" % create_jwt(),
    }

    url = f"/app/installations"
    api_base_url = "https://api.github.com"
    api_url = f"{api_base_url}{url}"

    out = requests.get(api_url, headers=headers)

    return json.loads(out.content)


def get_repo_installation(repo_owner, repo_name):
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": "Bearer %s" % create_jwt(),
    }

    url = f"/repos/{repo_owner}/{repo_name}/installation"
    api_base_url = "https://api.github.com"
    api_url = f"{api_base_url}{url}"

    out = requests.get(api_url, headers=headers)
    return json.loads(out.content)


def get_installations(access_token):
    api_url = f"https://api.github.com/user/installations"

    headers = {
        "Accept": "application/vnd.github.machine-man-preview+json",
        "Authorization": "token %s" % access_token,
    }

    out = requests.get(api_url, headers=headers)

    return json.loads(out.content)


def get_installation_repositories(access_token, installations_id):
    api_url = (
        f"https://api.github.com/user/installations/{installations_id}/repositories"
    )

    headers = {
        "Accept": "application/vnd.github.machine-man-preview+json",
        "Authorization": "token %s" % access_token,
    }

    out = requests.get(api_url, headers=headers)

    return json.loads(out.content)


def get_app_installation_repositories(installation_access_token):
    api_url = f"https://api.github.com/installation/repositories"

    headers = {
        "Accept": "application/vnd.github.machine-man-preview+json",
        "Authorization": "token %s" % installation_access_token,
    }

    out = requests.get(api_url, headers=headers)

    return json.loads(out.content)


def create_check_run(repository_full_name, installation_access_token, payload):
    url = f"/repos/{repository_full_name}/check-runs"
    api_base_url = "https://api.github.com"
    api_url = f"{api_base_url}{url}"

    headers = {
        "Accept": "application/vnd.github.antiope-preview+json",
        "Authorization": "token %s" % installation_access_token,
    }

    out = requests.post(api_url, data=json.dumps(payload), headers=headers)
    return out


def get_repository(installation_id, repository_full_name):
    # TODO: move method to class so the access token is not created over and over again.
    installation_access_token = get_access_token(installation_id)

    url = f"/repos/{repository_full_name}"
    api_base_url = "https://api.github.com"
    api_url = f"{api_base_url}{url}"

    headers = {
        "Authorization": "token %s" % installation_access_token,
    }

    out = requests.get(api_url, headers=headers)
    return json.loads(out.content)


def check_github_webhook_secret(func):
    """
    Check if the request actually was sent by GitHub.
    """

    def wrapper(*args, **kwargs):
        request = args[0]
        secret = settings.GITHUB_WEBHOOK_SECRET.encode()
        signature = request.headers["X-Hub-Signature"]
        h = hmac.new(secret, digestmod=hashlib.sha1)
        h.update(request.body)
        my_signature = "sha1=%s" % h.hexdigest()

        if not constant_time_compare(my_signature, signature):
            raise Http404()

        return func(*args, **kwargs)

    return wrapper
