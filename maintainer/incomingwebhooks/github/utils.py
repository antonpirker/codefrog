import json
import time

import jwt
import requests
from django.conf import settings


def get_jwt_token():
    # Generate the JWT
    private_key = settings.GITHUB_PRIVATE_KEY.decode("utf-8")
    current_time = int(time.time())

    payload = {
        # issued at time
        'iat': current_time,
        # JWT expiration time (10 minute maximum)
        'exp': current_time + (10 * 60),
        # GitHub App's identifier
        'iss': settings.GITHUB_APP_IDENTIFIER,
    }

    token = jwt.encode(payload, private_key, algorithm='RS256').decode("utf-8")
    print("JWT: %s" % token)
    return token


def get_access_token(installation_id, reposity_id):
    headers = {
        'Accept': 'application/vnd.github.machine-man-preview+json',
        'Authorization': 'Bearer %s' % get_jwt_token(),
    }

    url = f'/app/installations/{installation_id}/access_tokens'
    api_base_url = 'https://api.github.com'
    api_url = f'{api_base_url}{url}'

    payload = {
        "repository_ids": [reposity_id],
        "permissions": {
            "checks": "write",
            "contents": "read"
        }
    }

    out = requests.post(api_url, data=json.dumps(payload), headers=headers)
    out = json.loads(out.content)
    token = out['token']
    print("Installation access token: %s" % token)
    return token


def create_check_run(repository_full_name, installation_access_token, payload):
    url = f'/repos/{repository_full_name}/check-runs'
    api_base_url = 'https://api.github.com'
    api_url = f'{api_base_url}{url}'

    headers = {
        'Accept': 'application/vnd.github.antiope-preview+json',
        'Authorization': 'token %s' % installation_access_token,
    }

    out = requests.post(api_url, data=json.dumps(payload), headers=headers)
    return out
