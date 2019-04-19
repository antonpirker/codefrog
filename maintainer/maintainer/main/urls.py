from django.urls import path

from maintainer.main.views import index, update

urlpatterns = [
    path('', index),
    path('update', update),
]
