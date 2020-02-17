from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('', include('core.urls')),
    path('admin/', admin.site.urls),
    path('connectors/github/', include('connectors.github.urls')),
    path('connectors/fastspring/', include('connectors.fastspring.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
