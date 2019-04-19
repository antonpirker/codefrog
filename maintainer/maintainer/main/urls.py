from django.urls import path

from maintainer.main.views import index, update, update_issues

urlpatterns = [
    path('', index),
    path('update', update),
    path('update_issues', update_issues),
]
