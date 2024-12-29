# chat/middleware.py

from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.models import User
from django.db import close_old_connections

@database_sync_to_async
def get_user(token_key):
    try:
        jwt_auth = JWTAuthentication()
        validated_token = jwt_auth.get_validated_token(token_key)
        user = jwt_auth.get_user(validated_token)
        return user
    except Exception:
        return AnonymousUser()

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # Get the token from the query string
        token_key = ''
        query_string = scope['query_string'].decode()
        if 'token=' in query_string:
            token_key = query_string.split('token=')[1]

        scope['user'] = await get_user(token_key)
        return await super().__call__(scope, receive, send)
