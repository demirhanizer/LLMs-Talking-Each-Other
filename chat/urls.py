from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),  # Simple view for testing
]