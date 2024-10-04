# chat/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('create_persona/', views.create_persona, name='create_persona'),
    path('create_message/', views.create_message, name='create_message'),
    path('register/', views.register_user, name='register_user'),
    path('ws/llm/gpt-3/', views.gpt_3_view, name='gpt_3'),
    path('api/message_exchange/', views.message_exchange, name='message_exchange'),

]
