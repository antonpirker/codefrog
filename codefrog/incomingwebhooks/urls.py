from django.urls import path

from incomingwebhooks.views import payment

urlpatterns = [
    path('payment', payment),
]
