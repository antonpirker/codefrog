from django.urls import include, path
from rest_framework_nested import routers

from api_internal import views

router = routers.SimpleRouter()
router.register(r'projects', views.ProjectViewSet, basename='projects')

projects_router = routers.NestedSimpleRouter(router, r'projects', lookup='project')
projects_router.register(r'metrics', views.MetricViewSet, basename='metrics')
projects_router.register(r'releases', views.ReleaseViewSet, basename='releases')
projects_router.register(r'file-changes', views.FileChangesViewSet, basename='file-changes')
projects_router.register(r'source-status', views.SourceStatusViewSet, basename='source-status')

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('', include(router.urls)),
    path('', include(projects_router.urls)),
    path('api_internal-auth/', include('rest_framework.urls', namespace='rest_framework'))
]