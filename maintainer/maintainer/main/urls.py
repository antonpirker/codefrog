from django.urls import path

from maintainer.main import views

urlpatterns = [
    path('', views.index),
    path('update', views.update),
]
