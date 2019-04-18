from django.contrib import admin
from django.urls import path

from maintainer.githooks.views import merge_request_webhook
from maintainer.main.views import index


urlpatterns = [
    path('', index),
    path('incoming_merge_request_webhook', merge_request_webhook),

    path('admin/', admin.site.urls),
]
