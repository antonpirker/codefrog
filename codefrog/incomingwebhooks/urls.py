from django.urls import path

from incomingwebhooks.views import authorization, hook, setup, payment

urlpatterns = [
    path('hook', hook),
    path('setup', setup),
    path('authorization', authorization),
    path('payment', payment),
]
