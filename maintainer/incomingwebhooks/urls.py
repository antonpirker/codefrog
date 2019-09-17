from django.urls import path

from incomingwebhooks.views import gitlab_merge_request, github_apps_webhook

urlpatterns = [
    path('gitlab_merge_request', gitlab_merge_request),
    path('github_apps_webhook', github_apps_webhook),
]
