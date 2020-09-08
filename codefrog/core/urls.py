from django.urls import path, include

from core import views


def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path('', views.index, name='index'),

    # project details
    path('project/<slug:slug>/file-stats',
        views.project_file_stats, name='project-file-stats'),
    path('project/<slug:slug>',
        views.project_detail, name='project-detail'),

    # settings actions
    path('settings/<slug:username>/project/<slug:project_slug>/toggle',
        views.project_toggle, name='project-toggle'),

    path('accounts/', include('django.contrib.auth.urls')),

    # usage statistics
    path('count', views.count_usage),

    path('', include('web.urls')),

    path('sentry-debug/', trigger_error),
]
