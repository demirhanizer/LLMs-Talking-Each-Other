# chat/urls.py
from django.urls import path
from . import views
from .views import GetUserView, get_user_by_username, get_messages_by_user_and_persona, login_user, get_all_personas

urlpatterns = [
    path('create_persona/', views.create_persona, name='create_persona'),
    path('create_message/', views.create_message, name='create_message'),
    path('register/', views.register_user, name='register_user'),
    path('ws/llm/gpt-3/', views.gpt_3_view, name='gpt_3'),
    path('api/message_exchange/', views.message_exchange, name='message_exchange'),
    path('persona/name/<str:persona_name>/', views.get_persona, name='get_persona'),
    path('user/<str:username>/', get_user_by_username, name='get_user_by_username'),
    path('messages/<str:username>/<str:persona_name>/', get_messages_by_user_and_persona,
         name='get_messages_by_user_and_persona'),
    path('login/', login_user, name='login_user'),
    path('get_all_personas/', get_all_personas, name='get_all_personas'),

]
