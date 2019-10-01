from django.urls import path, include

from core import views
import django.contrib.auth.views as auth_views

urlpatterns = [
    path('', views.index, name='index'),

    # project actions
    path('project/<slug:slug>/toggle',
        views.project_toggle, name='project-toggle'),

    # project details
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

    path('accounts/', include('django.contrib.auth.urls')),
]
