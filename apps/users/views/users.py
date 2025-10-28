# -*- coding: utf-8 -*-
import json
import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Prefetch
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer, extend_schema_view
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, serializers
from rest_framework.decorators import action
from rest_framework.exceptions import (
    ValidationError,
    NotFound, PermissionDenied,
)
from rest_framework.generics import GenericAPIView, RetrieveAPIView
from rest_framework.mixins import (
    CreateModelMixin,
    RetrieveModelMixin,
    ListModelMixin,
    DestroyModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny, OR
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from apps.events.permissions import IsPasswordConfirmed
from apps.notifications.signals.initializers import send_email_signal
from apps.users.filters import UserFilter
from apps.users.models import AppRole
from apps.users.permissions import HasAppAdminPermissionFor
from apps.users.serializers import (
    UpdateUserSerializer,
    UserSerializer,
    ChangePasswordSerializer,
    UpdateUserPhoneOrEmailSerializer, AdminUserSerializer,
)
from apps.users.serializers.auth import CheckUserExistsSerializer
from apps.users.serializers.extras import SetRoleRequestSerializer, UserOrganizationInfoSerializer
from apps.utils.utils.baseviews import BaseModelMixin
from apps.xlib.error_util import ErrorEnum, ErrorUtil
from apps.organizations.models import Organization, OrganizationMembership, Role, Subscription


User = get_user_model()

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


# Create your viewsets here.
class RegisterView(GenericAPIView, CreateModelMixin):
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UserSerializer(user, context={"request": request}).data,
        }
        if user.email and user.email != '':
            send_email_signal.send(sender='RegisterView', instance=self,
                                   email_data={
                                       "params": {
                                           "user_id": str(user.pk),
                                           "email": user.email,
                                           'full_name': user.get_full_name(),
                                       },
                                       "email_type": 'welcome'
                                   }
                                   )

        return Response(data, status=status.HTTP_201_CREATED)
        

class PseudoAnonymousRegisterView(GenericAPIView, CreateModelMixin):
    permission_classes = [AllowAny]
    serializer_class = CheckUserExistsSerializer
    
    @extend_schema(
        request=CheckUserExistsSerializer,
        responses={
            201: UserSerializer(),
            400: inline_serializer(
                name='UserExistsError',
                fields={
                    'detail': serializers.CharField()
                }
            )
        },
        description="Créer un utilisateur anonyme avec l'email et/ou le numéro de téléphone fourni."
    )
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # Valider les données avec CheckUserExistsSerializer
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Récupérer l'email et le phone validés
        email = serializer.validated_data.get('email')
        phone = serializer.validated_data.get('phone')
        
        # Créer ou récupérer l'utilisateur anonyme
        user = User.objects.get_or_create_anonymous_user(email=email, phone=phone)
        
        # data = {
        #     "pk": user.id,
        #     "email": user.email,
        #     "phone": user.phone
        # }
        
        # Retourner les données de l'utilisateur avec le sérialiseur approprié
        return Response(
            UserSerializer(user).data, 
            status=status.HTTP_201_CREATED
        )


class RetrieveUserView(GenericAPIView, RetrieveModelMixin):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = UserSerializer

    def get_object(self):
        request = self.request
        user_pk = request.query_params.get("user_pk", None)
        if user_pk:
            permission_checker = HasAppAdminPermissionFor("Admin-Operation-User-Retrieve")
            if not permission_checker.has_permission(request, self):
                raise PermissionDenied(
                    ErrorUtil.get_error_detail(ErrorEnum.RESOURCE_RESERVED_TO_ADMIN),
                    code=ErrorEnum.RESOURCE_RESERVED_TO_ADMIN.value,
                )
            queryset = User.objects.filter(pk=user_pk)
            if not queryset.exists():
                raise NotFound(
                    ErrorUtil.get_error_detail(ErrorEnum.USER_NOT_FOUND),
                    code=ErrorEnum.USER_NOT_FOUND.value,
                )
            return queryset.first()

        return request.user

    @extend_schema(
        description="Endpoint to retrieve user info",
        parameters=[
            OpenApiParameter('user_pk', OpenApiTypes.UUID, location=OpenApiParameter.QUERY, required=False,
                             description="Use in case of admin request. Once specified in the query, "
                                         "the system will check admin right before process the request."
                             ),
        ],
    )
    @swagger_auto_schema(
        operation_id="Admin-Operation-User-Retrieve",
        operation_description="Récupérer les détails d' un utilisateur",
        operation_summary="Utilisateurs"
    )
    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class UpdateUserInfosView(GenericAPIView, UpdateModelMixin):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = UpdateUserSerializer

    def get_object(self):
        request = self.request
        user_pk = request.query_params.get("user_pk", None)
        if user_pk:
            permission_checker = HasAppAdminPermissionFor("Admin-Operation-User-Update")
            if not permission_checker.has_permission(request, self):
                raise PermissionDenied(
                    ErrorUtil.get_error_detail(ErrorEnum.RESOURCE_RESERVED_TO_ADMIN),
                    code=ErrorEnum.RESOURCE_RESERVED_TO_ADMIN.value,
                )
            queryset = User.objects.filter(pk=user_pk)
            if not queryset.exists():
                raise NotFound(
                    ErrorUtil.get_error_detail(ErrorEnum.USER_NOT_FOUND),
                    code=ErrorEnum.USER_NOT_FOUND.value,
                )
            return queryset.first()
        return self.request.user

    @extend_schema(
        description="Endpoint to update user infos",
        parameters=[
            OpenApiParameter('password', OpenApiTypes.STR, location=OpenApiParameter.QUERY,
                             description="The user's password"),
            OpenApiParameter('user_pk', OpenApiTypes.UUID, location=OpenApiParameter.QUERY, required=False,
                             description="Use in case of admin request. Once specified in the query, "
                                         "the system will check admin right before process the request."
                             ),
        ],
    )
    @swagger_auto_schema(
        operation_id="Admin-Operation-User-Update",
        operation_description="Mettre à jour un utilisateur",
        operation_summary="Utilisateurs"
    )
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class UpdateUserEmailOrPhoneView(GenericAPIView, UpdateModelMixin):
    permission_classes = [IsAuthenticated, IsPasswordConfirmed]
    authentication_classes = [JWTAuthentication]
    serializer_class = UpdateUserPhoneOrEmailSerializer

    def get_object(self):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.validated_data)


# Todo: Cache
@method_decorator(name='get', decorator=swagger_auto_schema(
    operation_id="Admin-Operation-User-List",
    operation_description="Lister les utilisateurs",
    operation_summary="Utilisateurs"
))
class UsersListView(GenericAPIView, ListModelMixin):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    permission_classes = [IsAuthenticated, OR(IsAdminUser(), HasAppAdminPermissionFor("Admin-Operation-User-List"))]
    authentication_classes = [JWTAuthentication]

    filterset_class = UserFilter

    def get_permissions(self):
        def get_permission_function(instance):
            try:
                return instance()
            except TypeError:
                return instance

        return [get_permission_function(permission) for permission in self.permission_classes]

    @extend_schema(
        description="Endpoint to get users list",
        parameters=[
            OpenApiParameter('is_event_organizer', OpenApiTypes.BOOL, location=OpenApiParameter.QUERY, required=False,
                             description="Filter by user that have organizer status"),
            OpenApiParameter('is_staff', OpenApiTypes.BOOL, location=OpenApiParameter.QUERY, required=False,
                             description="Filter by admin users"),
        ],
    )
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# TODO Implement the best flow for account deletion
# TODO Use this view as total destroyer,

class DestroyUserView(GenericAPIView, DestroyModelMixin):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdminUser, IsPasswordConfirmed]
    authentication_classes = [JWTAuthentication]

    def get_object(self):
        try:
            instance = User.objects.get(pk=self.request.user.pk)
        except Exception as exc:
            logger.exception(exc.__str__())
            raise NotFound("Nous n' avons pas trouvé cet utilisateur .")
        return instance

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class DeactivateUserView(GenericAPIView, DestroyModelMixin):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # Todo: ReThink the permission classes enhancement
    permission_classes = [
        IsAuthenticated,
        OR(
            IsPasswordConfirmed(),
            HasAppAdminPermissionFor("Admin-Operation-User-Deactivate")
        )
    ]
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        def get_permission_function(instance):
            try:
                return instance()
            except TypeError:
                return instance

        return [get_permission_function(permission) for permission in self.permission_classes]

    @extend_schema(
        description="Endpoint to deactivate an user",
        parameters=[
            OpenApiParameter('user_pk', OpenApiTypes.UUID, location=OpenApiParameter.QUERY, required=False,
                             description="Use in case of admin request. Once specified in the query, "
                                         "the system will check admin right before process the request."
                             ),
        ],
    )
    @swagger_auto_schema(
        operation_id="Admin-Operation-User-Deactivate",
        operation_description="Désactiver un utilisateur",
        operation_summary="Utilisateurs"
    )
    def delete(self, request, *args, **kwargs):
        user_pk = request.query_params.get("user_pk", None)

        q = Q(pk=request.user.pk)

        if user_pk:
            permission_checker = HasAppAdminPermissionFor("Admin-Operation-User-Deactivate")
            if not permission_checker.has_permission(request, self):
                raise PermissionDenied(
                    ErrorUtil.get_error_detail(ErrorEnum.RESOURCE_RESERVED_TO_ADMIN),
                    code=ErrorEnum.RESOURCE_RESERVED_TO_ADMIN.value,
                )
            q = Q(pk=user_pk)

        queryset = self.queryset.filter(q)

        if not queryset.exists():
            raise NotFound(
                ErrorUtil.get_error_detail(ErrorEnum.USER_NOT_FOUND),
                code=ErrorEnum.USER_NOT_FOUND.value,
            )

        queryset.update(deactivated_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = ChangePasswordSerializer

    @extend_schema(
        responses={
            202: inline_serializer(
                name="ChangePasswordResponseSerializer",
                fields={
                },
            )
        }
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_password = serializer.validated_data.get("old_password", "")
        new_password = serializer.validated_data.get("new_password", "")
        if old_password == "":
            raise ValidationError({"old_password": "Ce champs ne peut être vide"})
        if not user.check_password(old_password):
            raise ValidationError({"message": "Mot de passe actuel incorrect."})
        if new_password == "":
            raise ValidationError({"new_password": "Ce champs ne peut être vide"})
        user.set_password(new_password)
        user.save()
        return Response(status=status.HTTP_202_ACCEPTED)


class ManageUserProfileImageView(GenericAPIView):
    permission_classes = [
        # IsAuthenticated, OR(IsAdminUser(), HasAppAdminPermissionFor("Admin-Operation-Manage-User-Profile-Image"))
        IsAuthenticated,
    ]

    def get_permissions(self):
        def get_permission_function(instance):
            try:
                return instance()
            except TypeError:
                return instance

        return [get_permission_function(permission) for permission in self.permission_classes]

    def delete(self, request, *args, **kwargs):
        user = request.user
        try:
            user.profile_image.delete()
            user.save()
        except Exception as exc:
            logger.exception(exc.__str__())
            raise ValidationError(
                {"message": "Une erreur s' est produite, veuillez réessayer"},
                code=ErrorEnum.SERVER_ERROR.value,
            )

        return Response({"status": "OK"}, status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=inline_serializer(
            name="ManageUserProfileImageViewRequestSerializer",
            fields={
                "profile_image": serializers.FileField(),
            },
        ),
        responses={200: json.dumps({"status": "OK"})}
    )
    @swagger_auto_schema(
        operation_id="Admin-Operation-Manage-User-Profile-Image",
        operation_description="Gérer l' image de profile d' un utilisateur",
        operation_summary="Utilisateurs"
    )
    def post(self, request, *args, **kwargs):
        user = request.user
        try:
            profile_image = request.FILES["profile_image"]
        except Exception as exc:
            logger.exception(exc.__str__())
            raise ValidationError(
                {"profile_image": "Le champs profile_image n' est pas valide"}
            )

        try:
            user.profile_image = profile_image
            user.save()
        except Exception as exc:
            logger.exception(exc.__str__())
            raise ValidationError(
                {"message": "Une erreur s' est produite, veuillez réessayer"},
                code=ErrorEnum.SERVER_ERROR.value,
            )

        return Response({"status": "OK"}, status=status.HTTP_200_OK)


@extend_schema_view(
    update=extend_schema(
        description="Endpoint to set user role in the app",
        request=SetRoleRequestSerializer(),
        responses={201: AdminUserSerializer()}
    )
)
@method_decorator(
    name="set_role",
    decorator=swagger_auto_schema(
        operation_id="Admin-Operation-User-Set-Role",
        operation_description="Définir le rôle dans l' application d' un utilisateur",
        operation_summary="Utilisateurs",
    ),
)
class UserViewSet(BaseModelMixin, GenericViewSet):
    object_class = User
    serializer_default_class = UserSerializer

    http_method_names = ["put"]

    permission_classes_by_action = {
        "set_role": [
            IsAuthenticated,
            OR(
                IsAdminUser(),
                HasAppAdminPermissionFor("Admin-Operation-Set-User-Role"),
            ),
        ]
    }

    serializer_classes_by_action = {
        "set_role": SetRoleRequestSerializer,
    }

    def get_queryset(self):
        return self.object_class.objects.all()

    @action(methods=["PUT"], detail=True, url_path="set-role")
    def set_role(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        role = serializer.validated_data.get('role')
        try:
            app_role = role if role is None else AppRole.objects.get(label=role)
        except AppRole.DoesNotExist:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.APP_ROLE_DOES_NOT_EXIST),
                code=ErrorEnum.APP_ROLE_DOES_NOT_EXIST.value,
            )

        user.role = app_role
        user.save(update_fields=["role"])

        return Response(AdminUserSerializer(user).data, status=status.HTTP_202_ACCEPTED)
    

class RetrieveUserOrganizationInfoView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = UserOrganizationInfoSerializer
    
    def get_queryset(self):
        return User.objects.filter(pk=self.request.user.pk).prefetch_related(
            Prefetch(
                'organizations_own',
                queryset=Organization.objects.all().prefetch_related('subscriptions'),
                to_attr='owned_orgs'
            ),
            Prefetch(
                'memberships',
                queryset=OrganizationMembership.objects.select_related('organization')
                    .prefetch_related('roles'),
                to_attr='user_memberships'
            )
        )

    def get_object(self):
        user = self.get_queryset().first()
        if not user:
            raise NotFound(
                ErrorUtil.get_error_detail(ErrorEnum.USER_NOT_FOUND),
                code=ErrorEnum.USER_NOT_FOUND.value,
            )
        return user

    @extend_schema(
        description="Endpoint to retrieve user info",
        responses={200: UserOrganizationInfoSerializer}
    )
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        print(response.data)
        return Response(response.data, status=response.status_code)
