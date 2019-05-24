from django.urls import path

from incomingwebhooks.views import gitlab_merge_request

urlpatterns = [
    path('gitlab_merge_request', gitlab_merge_request),
]
