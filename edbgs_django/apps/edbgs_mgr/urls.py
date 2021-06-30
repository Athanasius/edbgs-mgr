"""ED BGS Manager Django URL routing."""
from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
]
