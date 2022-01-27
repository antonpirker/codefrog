from django.urls import path, include

from web import views

urlpatterns = [
    path("connect-github", views.connect_github, name="connect-github"),
    path("pricing", views.pricing, name="pricing"),
    # settings
    path("settings/<slug:username>", views.user_settings, name="user-settings"),
    path(
        "settings/<slug:username>/project/<slug:project_slug>",
        views.project_settings,
        name="project-settings",
    ),
]
