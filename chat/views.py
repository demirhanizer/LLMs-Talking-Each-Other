# chat/views.py
from django.http import HttpResponse
from .models import LLMPersona, Message
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserRegistrationSerializer
from django.http import JsonResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import LLMPersona
from django.contrib.auth.models import User
import json


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def create_persona(request):
    if request.method == 'POST':
        try:
            # The authenticated user from the JWT token
            user = request.user

            # Parse the request body data
            data = json.loads(request.body)
            persona_name = data.get('name', 'Default Persona')  # Get name, default to 'Default Persona'
            personality_traits = data.get('personality_traits', {"trait": "friendly"})  # Default trait if none provided

            # Create the LLM Persona for the authenticated user
            persona = LLMPersona.objects.create(
                user=user,
                name=persona_name,
                personality_traits=personality_traits
            )

            return JsonResponse({
                'status': 'success',
                'message': f'Persona {persona.name} created successfully',
                'persona_id': persona.id
            }, status=201)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


def create_message(request):
    user = get_object_or_404(User, id=1)  # Again, assume user with id 1 exists
    persona = get_object_or_404(LLMPersona, id=1)  # Assume persona with id 1 exists
    message = Message.objects.create(sender=user, persona=persona, content="Hello from the user", is_from_user=True)
    return HttpResponse(f"Created message: {message.content}")


@api_view(['POST'])
def register_user(request):
    if request.method == 'POST':
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            # Create the user
            user = serializer.save()
            return Response({
                'status': 'success',
                'message': f'User {user.username} created successfully'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
