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
class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE)  # The sender of the message (user)
    persona = models.ForeignKey(LLMPersona, on_delete=models.CASCADE)  # Which persona is involved in the message
    content = models.TextField()  # The actual message content
    response = models.TextField(null=True, blank=True)  # The LLM's response (can be empty initially)
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for message creation
    is_from_user = models.BooleanField(default=True)  # Distinguishes between user and LLM messages

    def __str__(self):
        return f"Message from {self.sender.username} at {self.created_at}"
