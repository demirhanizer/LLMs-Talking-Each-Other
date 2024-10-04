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

from django.http import HttpResponse

def gpt_3_view(request):
    return HttpResponse("This is the GPT-3 response.")

from django.http import JsonResponse
from .models import Message, LLMPersona
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth.models import User

@csrf_exempt
def message_exchange(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        message_content = data.get('message')

        # Ensure the user is authenticated or get the user (this will depend on your authentication system)
        if request.user.is_authenticated:
            user = request.user
        else:
            # For testing purposes, if the user is not authenticated, you can create or assign a default user.
            user = User.objects.first()  # In real cases, raise an error or redirect to login

        # Ensure there is a persona associated with the user
        persona = LLMPersona.objects.filter(user=user).first()
        if not persona:
            # Create a default persona if none exists
            persona = LLMPersona.objects.create(user=user, name="Default Persona", personality_traits={"trait": "friendly"})

        # Simulate a response from LLM
        response_content = f"Echo: {message_content}"

        # Create the message with the user as the sender
        message = Message.objects.create(
            sender=user,
            persona=persona,
            content=message_content,
            response=response_content,  # Store the LLM's response
            is_from_user=True
        )

        return JsonResponse({'message': message_content, 'response': response_content})

    return JsonResponse({'error': 'Invalid request'}, status=400)
