from django.urls import path

from maintainer.main import views

urlpatterns = [
    path('', views.index),
    path('update', views.update),
    path('update_issues', views.update_issues),
    path('update_errors', views.update_errors),
]
