from django.urls import path

from connectors.fastspring import views

urlpatterns = [
    path('fastspring', views.payment),
]
