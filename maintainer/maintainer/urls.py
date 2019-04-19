from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('', include('maintainer.main.urls')),
    path('incoming/', include('maintainer.incomingwebhooks.urls')),

    path('admin/', admin.site.urls),
]
