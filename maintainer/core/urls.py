from django.urls import path

from core import views

urlpatterns = [
    path('', views.index, name='index'),

    path('project/<slug:slug>',
        views.project_detail, name='project-detail'),
    path('project/<slug:slug>/<slug:zoom>',
        views.project_detail, name='project-detail-zoomed'),
    path('project/<slug:slug>/<slug:zoom>/<slug:release_flag>',
        views.project_detail, name='project-detail-zoomed-release'),

    path('settings/<slug:username>',
        views.user_settings, name='user_settings'),
    path('settings/<slug:username>/project/<slug:project_slug>',
        views.project_settings, name='project_settings'),
]
