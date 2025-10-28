# -*- coding: utf-8 -*-
"""
Vues API REST pour les salons de discussion.
"""

import logging
from django.db.models import Count

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework.serializers import UUIDField, CharField

from apps.chat_rooms.models import ChatRoom
from apps.chat_rooms.serializers.chat_room import ChatRoomSerializer
from apps.chat_rooms.serializers.access_criteria import ChatRoomAccessCriteriaSerializer
from apps.organizations.permissions import (
    IsOrganizationMember,
    IsOrganizationEventManager,
)
from apps.utils.utils.baseviews import BaseModelsViewSet
from apps.organizations.models import Organization
from apps.organizations.mixings import CheckParentPermissionMixin
from apps.xlib.enums import ChatRoomRolesEnum, ChatRoomStatusEnum, ChatRoomTypeEnum, ChatRoomVisibilityEnum, OrganizationRolesEnum
from apps.xlib.error_util import ErrorUtil, ErrorEnum

# Ajoute automatiquement les critères d'accès pour les membres et le propriétaire
from apps.chat_rooms.models import ChatRoomAccessCriteria, ChatRoomSubscription
from apps.xlib.enums import AccessCriteriaTypeEnum, ChatRoomRolesEnum

logger = logging.getLogger(__name__)

User = get_user_model()

@extend_schema(
    description="API pour la gestion des salons de discussion au sein d'une organisation."
)
class WriteChatRoomViewSet(CheckParentPermissionMixin, BaseModelsViewSet):
    """ViewSet en écriture pour les salons de chat, imbriqué sous les organisations.

    Permet aux membres d'une organisation de :
    - Créer des salons de discussion
    - Modifier les paramètres des salons
    - Supprimer des salons (réservé aux gestionnaires d'événements)
    - Gérer les critères d'accès aux salons
    """

    serializer_default_class = ChatRoomSerializer
    parent_queryset = Organization.objects.filter(active=True)
    parent_lookup_field = "pk"
    parent_lookup_url_kwarg = "organization_pk"

    permission_classes_by_action = {
        "create": [IsAuthenticated, IsOrganizationMember],
        "update": [IsAuthenticated, IsOrganizationMember],
        "partial_update": [IsAuthenticated, IsOrganizationMember],
        "destroy": [IsAuthenticated, IsOrganizationEventManager],
        "add_access_criteria": [IsAuthenticated, IsOrganizationEventManager],
    }

    @extend_schema(
        summary="Liste des salons de l'organisation",
        description="Récupère la liste des salons de discussion associés aux événements de l'organisation.",
    )
    def get_queryset(self):
        """Retourne les salons de l'organisation."""
        return ChatRoom.objects.filter(event__organization=self.parent_obj).distinct()

    def perform_create(self, serializer):
        """Crée un salon en l'associant à l'organisation."""
        event = serializer.validated_data.get("event_id")

        if event.organization != self.parent_obj:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.INVALID_EVENT_DATA),
                code=ErrorEnum.INVALID_EVENT_DATA.value,
            )

        # Crée le salon
        try:
            chat_room = serializer.save(event=event)
        except Exception as e:
            logger.error(f"Erreur lors de la création du salon: {str(e)}")
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.CHAT_ROOM_ALREADY_EXISTS),
                code=ErrorEnum.CHAT_ROOM_ALREADY_EXISTS.value,
            )


        # Ajoute les critères d'accès si le salon est privé
        if chat_room.visibility == ChatRoomVisibilityEnum.PRIVATE.value:
            ChatRoomAccessCriteria.objects.create(
                chat_room=chat_room,
                criteria_type=AccessCriteriaTypeEnum.ROLE.value,
                criteria_rules={
                    "required_roles": [
                        OrganizationRolesEnum.MEMBER.value,
                        OrganizationRolesEnum.COORDINATOR.value,
                    ]
                },
            )

        # Inscrit automatiquement le propriétaire et les membres de l'organisation
        organization = self.parent_obj

        # Inscrit le propriétaire comme admin
        if organization.owner:
            try:
                ChatRoomSubscription.objects.create(
                    chat_room=chat_room,
                    user=organization.owner,
                    role=ChatRoomRolesEnum.ADMIN.value,
                    username=organization.owner.username,
                )
            except Exception as e:
                logger.warning(
                    f"Échec de l'inscription du propriétaire {organization.owner.pk} au salon {chat_room.pk}: {str(e)}"
                )

        # Inscrit les membres comme utilisateurs
        for membership in organization.memberships.all():
            if membership.user != organization.owner:
                try:
                    ChatRoomSubscription.objects.create(
                        chat_room=chat_room,
                        user=membership.user,
                        role=ChatRoomRolesEnum.ADMIN.value,
                        username=membership.user.username,
                    )
                except Exception as e:
                    logger.warning(
                        f"Échec de l'inscription du membre {membership.user.pk} au salon {chat_room.pk}: {str(e)}"
                    )

        return chat_room

    @extend_schema(
        summary="Création d'un salon",
        description="Crée un nouveau salon de discussion pour un événement de l'organisation.",
        request=ChatRoomSerializer,
        responses={201: ChatRoomSerializer},
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        request=ChatRoomAccessCriteriaSerializer,
        responses={201: ChatRoomAccessCriteriaSerializer},
    )
    @action(detail=True, methods=["post"])
    def add_access_criteria(self, request, organization_pk=None, pk=None):
        room = self.get_object()
        serializer = ChatRoomAccessCriteriaSerializer(data=request.data)

        if serializer.is_valid():
            try:
                criteria = serializer.save(chat_room=room)
                logger.info(
                    f"Critère d'accès {criteria.pk} ajouté au salon {room.pk} "
                    f"par {request.user.pk}"
                )
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Erreur lors de l'ajout du critère d'accès: {str(e)}")
                return ValidationError(
                    ErrorUtil.get_error_detail(
                        ErrorEnum.CANNOT_ADD_CRITERIA_T0_CHAT_ROOM
                    ),
                    code=ErrorEnum.CANNOT_ADD_CRITERIA_T0_CHAT_ROOM.value,
                )

        return ValidationError(
            ErrorUtil.get_error_detail(ErrorEnum.CANNOT_ADD_CRITERIA_T0_CHAT_ROOM),
            code=ErrorEnum.CANNOT_ADD_CRITERIA_T0_CHAT_ROOM.value,
        )

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


    @extend_schema(
        summary="Création d'un salon personnel",
        description="Crée un nouveau salon personnel pour un utilisateur.",
        request=inline_serializer(
            name='StartChatRoomSerializer',
            fields={
                'user_pk': UUIDField(required=True, help_text="ID de l'utilisateur avec qui démarrer le salon"),
                'event_id': UUIDField(required=True, help_text="ID de l'événement associé au salon"),
                'title': CharField(required=False, help_text="Titre du salon personnel")
            }
        ),
        responses={201: ChatRoomSerializer},
    )
    @action(detail=False, methods=["post"])
    def start_chat_room(self, request, organization_pk=None):
        organization = self.parent_obj

        # Current authenticated user (initiator)
        user = request.user
        if not user:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.USER_NOT_FOUND),
                code=ErrorEnum.USER_NOT_FOUND.value,
            )

        # Validate interlocutor and event
        interlocutor_pk = request.data.get("user_pk")
        event_id = request.data.get("event_id")
        if not interlocutor_pk:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.INTERLOCUTOR_REQUIRED),
                code=ErrorEnum.INTERLOCUTOR_REQUIRED.value,
            )
        if not event_id:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.EVENT_REQUIRED),
                code=ErrorEnum.EVENT_REQUIRED.value,
            )

        # Fetch interlocutor and event
        try:
            interlocutor = User.objects.get(pk=interlocutor_pk)
        except User.DoesNotExist:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.USER_NOT_FOUND),
                code=ErrorEnum.USER_NOT_FOUND.value,
            )
        # Note: self-chat behavior not explicitly restricted by ErrorEnum; allow or handle at business layer if needed

        from apps.events.models import Event
        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.EVENT_NOT_FOUND),
                code=ErrorEnum.EVENT_NOT_FOUND.value,
            )
        # Ensure the event belongs to the current organization context
        if event.organization != organization:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.INVALID_EVENT_DATA),
                code=ErrorEnum.INVALID_EVENT_DATA.value,
            )

        payload = {
            "type": ChatRoomTypeEnum.PERSONAL.value,
            "visibility": ChatRoomVisibilityEnum.PRIVATE.value,
            "event_id": event_id,
            "status": ChatRoomStatusEnum.ACTIVE.value,
            "title": request.data.get("title")
        }
        serializer = self.get_serializer(data=payload)
        serializer.is_valid(raise_exception=True)
        # Try to restore an existing personal room (even if soft-deleted)
        # This allows re-using a previously deleted room/subscriptions between the same two users for the same event.
        existing = ChatRoom.objects.filter(
            type=ChatRoomTypeEnum.PERSONAL.value,
            event=event,
            subscriptions__user=user,
        ).filter(
            subscriptions__user=interlocutor,
        ).distinct().first()
        if not existing:
            # Look into soft-deleted subscriptions to find a matching room between both users
            from apps.chat_rooms.models import ChatRoomSubscription
            pair_room = (
                ChatRoomSubscription.deleted_objects
                .filter(
                    user__in=[user, interlocutor],
                    chat_room__event=event,
                    chat_room__type=ChatRoomTypeEnum.PERSONAL.value,
                    is_deleted=True,
                )
                .values("chat_room")
                .annotate(users_count=Count("user", distinct=True))
                .filter(users_count=2)
                .order_by("chat_room")
                .first()
            )
            if pair_room:
                room_id = pair_room["chat_room"]
                existing = ChatRoom.deleted_objects.filter(pk=room_id).first() or ChatRoom.objects.filter(pk=room_id).first()

        if existing:
            # If both subscriptions are active and room is not deleted, prevent duplicate creation
            active_subs_count = ChatRoomSubscription.objects.filter(
                chat_room=existing, user__in=[user, interlocutor], is_deleted=False
            ).count()
            if active_subs_count == 2 and not getattr(existing, "is_deleted", False):
                raise ValidationError(
                    ErrorUtil.get_error_detail(ErrorEnum.CHAT_ROOM_ALREADY_EXISTS),
                    code=ErrorEnum.CHAT_ROOM_ALREADY_EXISTS.value,
                )

            # Restore room if soft-deleted
            if getattr(existing, "is_deleted", False):
                try:
                    existing = existing.restore()
                except Exception:
                    # Fallback in unlikely case restore() is unavailable
                    existing.is_deleted = False
                    if hasattr(existing, "deleted_at"):
                        existing.deleted_at = None
                    existing.save(update_fields=["is_deleted", "deleted_at"] if hasattr(existing, "deleted_at") else ["is_deleted"])

            # Ensure both subscriptions exist and are active
            for target_user in (user, interlocutor):
                deleted_sub = ChatRoomSubscription.deleted_objects.filter(
                    chat_room=existing,
                    user=target_user,
                    is_deleted=True,
                ).first()
                if deleted_sub:
                    try:
                        deleted_sub.restore()
                    except Exception:
                        deleted_sub.is_deleted = False
                        if hasattr(deleted_sub, "deleted_at"):
                            deleted_sub.deleted_at = None
                        deleted_sub.save(update_fields=["is_deleted", "deleted_at"] if hasattr(deleted_sub, "deleted_at") else ["is_deleted"])
                    continue
                # Create subscription if none exists
                ChatRoomSubscription.objects.get_or_create(
                    chat_room=existing,
                    user=target_user,
                )

            # Return restored room
            restored_serializer = self.get_serializer(existing)
            return Response(restored_serializer.data, status=status.HTTP_200_OK)

        # Prevent duplicates: must match the SAME event and include BOTH users with active (not soft-deleted) subscriptions
        if ChatRoom.objects.filter(
            type=ChatRoomTypeEnum.PERSONAL.value,
            event=event,
            subscriptions__user=user,
            subscriptions__is_deleted=False,
        ).filter(
            subscriptions__user=interlocutor,
            subscriptions__is_deleted=False,
        ).distinct().exists():
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.CHAT_ROOM_ALREADY_EXISTS),
                code=ErrorEnum.CHAT_ROOM_ALREADY_EXISTS.value,
            )

        # Save the chat room for the specific event
        chat_room = serializer.save()
        
        try:
            # Subscribe the two participants. For a personal room, only the two users should be added.
            ChatRoomSubscription.objects.create(
                chat_room=chat_room,
                user=user,
                role=ChatRoomRolesEnum.ADMIN.value,
                username=user.username if user.username else f"{user.first_name} {user.last_name}",
            )
            ChatRoomSubscription.objects.create(
                chat_room=chat_room,
                user=interlocutor,
                role=ChatRoomRolesEnum.ADMIN.value,
                username=interlocutor.username if interlocutor.username else f"{interlocutor.first_name} {interlocutor.last_name}",
            )
        except Exception as e:
            logger.error(f"Erreur lors de la création des abonnements au salon: {str(e)}")
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.CHAT_ROOM_SUBSCRIPTION_ALREADY_EXISTS),
                code=ErrorEnum.CHAT_ROOM_SUBSCRIPTION_ALREADY_EXISTS.value,
            )

        return Response(serializer.data, status=status.HTTP_201_CREATED)