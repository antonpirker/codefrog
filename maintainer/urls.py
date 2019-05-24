from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('', include('core.urls')),
    path('incoming/', include('incomingwebhooks.urls')),

    path('admin/', admin.site.urls),
]
