# chat/models.py
from django.db import models
from django.contrib.auth.models import User

class LLMPersona(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    personality_traits = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    persona = models.ForeignKey(LLMPersona, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_from_user = models.BooleanField(default=True)
