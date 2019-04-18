from django.urls import path

from maintainer.incomingwebhooks.views import gitlab_merge_request

urlpatterns = [
    path('gitlab_merge_request', gitlab_merge_request),
]
