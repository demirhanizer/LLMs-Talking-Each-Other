# chat/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('create_persona/', views.create_persona, name='create_persona'),
    path('create_message/', views.create_message, name='create_message'),
    path('register/', views.register_user, name='register_user'),
]
