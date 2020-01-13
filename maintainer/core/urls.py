from django.urls import path, include

from core import views
import django.contrib.auth.views as auth_views

urlpatterns = [
    path('', views.index, name='index'),

    # project details
    path('project/<slug:slug>/file-stats',
        views.project_file_stats, name='project-file-stats'),
    path('project/<slug:slug>/<slug:zoom>/<slug:release_flag>',
        views.project_detail, name='project-detail-zoomed-release'),
    path('project/<slug:slug>/<slug:zoom>',
        views.project_detail, name='project-detail-zoomed'),
    path('project/<slug:slug>',
        views.project_detail, name='project-detail'),

    # settings
    path('settings/<slug:username>',
        views.user_settings, name='user-settings'),
    path('settings/<slug:username>/project/<slug:project_slug>',
        views.project_settings, name='project-settings'),

    # settings actions
    path('settings/<slug:username>/project/<slug:project_slug>/toggle',
        views.project_toggle, name='project-toggle'),

    path('accounts/', include('django.contrib.auth.urls')),

    # usage statistics
    path('count', views.count_usage)
]
