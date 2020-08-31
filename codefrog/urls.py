from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from web import views

urlpatterns = [
    path('', include('core.urls')),
    path('admin/', admin.site.urls),
    path('connectors/github/', include('connectors.github.urls')),
    path('connectors/fastspring/', include('connectors.fastspring.urls')),

    path('api-internal/', include('api_internal.urls')),

    # feedback
    path('feedback', views.feedback, name='feedback'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
