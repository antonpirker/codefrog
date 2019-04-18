from django.contrib import admin
from django.urls import path, include

from maintainer.main.views import index


urlpatterns = [
    path('', index),
    path('incoming/', include('maintainer.incomingwebhooks.urls')),

    path('admin/', admin.site.urls),
]
