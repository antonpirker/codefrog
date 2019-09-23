from django.urls import path

from incomingwebhooks.views import hook

urlpatterns = [
    path('hook', hook),
]
