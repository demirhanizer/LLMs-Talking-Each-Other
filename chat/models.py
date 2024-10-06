# chat/models.py
from django.db import models
from django.contrib.auth.models import User

# LLM Persona model
class LLMPersona(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Each persona belongs to a user
    name = models.CharField(max_length=100)  # Name of the persona
    personality_traits = models.JSONField()  # Store persona traits as JSON
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for persona creation

    def __str__(self):
        return f"{self.user.username} - {self.name}"

# Message model
# chat/models.py

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    persona = models.ForeignKey(LLMPersona, on_delete=models.CASCADE)
    content = models.TextField()
    response = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_from_user = models.BooleanField(default=True)

    def __str__(self):
        sender = self.sender.username if self.sender else 'LLM'
        return f"Message from {sender} at {self.created_at}"

