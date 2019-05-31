from django.urls import path

from core import views

urlpatterns = [
    path('', views.index, name='index'),
    path('project/<slug:slug>', views.project_detail, name='project-detail'),
]
