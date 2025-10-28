# -*- coding: utf-8 -*-

import logging

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView
from rest_framework import serializers

from apps.users.serializers.auth import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer, UserLogoutSerializer,
    CheckUserExistsSerializer,
)
from apps.users.serializers.extras import AuthResponseTypeSerializer
from apps.users.serializers import UserSerializer

User = get_user_model()

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


# Create your viewsets here.


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = TokenObtainPairSerializer

    @extend_schema(
        responses={200: AuthResponseTypeSerializer},
    )
    def post(self, request, *args, **kwargs):
        return super(TokenObtainPairView, self).post(request, *args, **kwargs)


class AdminLoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = TokenObtainPairSerializer

    @extend_schema(
        responses={200: AuthResponseTypeSerializer},
    )
    def post(self, request, *args, **kwargs):
        # for_app_admin: this attr design if the login request is for and app admin user
        request.for_app_admin = True
        return super(TokenObtainPairView, self).post(request, *args, **kwargs)


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    serializer_class = TokenRefreshSerializer

    @extend_schema(
        responses={200: AuthResponseTypeSerializer},
    )
    def post(self, request, *args, **kwargs):
        return super(TokenRefreshView, self).post(request, *args, **kwargs)


class LogoutView(GenericAPIView):
    serializer_class = UserLogoutSerializer
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        responses={
            204: inline_serializer(
                name="LogoutResponseSerializer",
                fields={
                },
            )
        }
    )
    def post(self, request, *args):
        sz = self.get_serializer(data=request.data)
        sz.is_valid(raise_exception=True)
        sz.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CheckUserExistsView(GenericAPIView):
    """
    Vérifie si un utilisateur existe avec l'email et/ou le numéro de téléphone fourni.
    Accessible sans authentification.
    """
    permission_classes = [AllowAny]
    serializer_class = CheckUserExistsSerializer
    
    @extend_schema(
        request=CheckUserExistsSerializer,
        responses={
            200: UserSerializer(),
            400: inline_serializer(
                name='UserExistsError',
                fields={
                    'detail': serializers.CharField()
                }
            )
        },
        description="Vérifie si un utilisateur existe avec l'email et/ou le numéro de téléphone fourni."
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
            
        email = serializer.validated_data.get('email')
        phone = serializer.validated_data.get('phone')
        
        user = None
        if email:
            user = User.global_objects.filter(email=email).first()
        
        if not user and phone:
            user = User.global_objects.filter(phone=phone).first()
        
        response_data = {
            'exists': user is not None,
        }
        
        if user:
            response_data['user'] = UserSerializer(user).data
        
        return Response(response_data, status=status.HTTP_200_OK)
