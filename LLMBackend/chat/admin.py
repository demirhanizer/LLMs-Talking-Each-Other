# chat/admin.py
from django.contrib import admin
from .models import LLMPersona, Message

admin.site.register(LLMPersona)
admin.site.register(Message)
