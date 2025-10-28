# -*- coding: utf-8 -*-
"""
Vues API REST pour les salons de discussion.
Optimisé pour une application à grande échelle avec des millions d'utilisateurs.
"""

import logging
 
from drf_spectacular.types import OpenApiTypes
from rest_framework import status, filters
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin,RetrieveModelMixin
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q


from apps.chat_rooms.models import ChatRoom
from apps.chat_rooms.serializers.chat_room import (
    ChatRoomSerializer, ChatRoomListSerializer
)
from apps.users.models import User
from apps.events.models import Event
from apps.chat_rooms.filters import ChatRoomFilter
from apps.chat_rooms.paginator import ChatRoomPagination
from apps.xlib.enums import ChatRoomVisibilityEnum, ChatRoomTypeEnum
from apps.utils.utils.baseviews import BaseGenericViewSet
from apps.xlib.error_util import ErrorEnum, ErrorUtil
from apps.chat_rooms.serializers.subscription import LightChatRoomSubscriptionSerializer
logger = logging.getLogger(__name__)

 
@extend_schema_view(
    list=extend_schema(
        summary="Liste des salons de discussion",
        description="Retourne une liste paginée des salons de discussion accessibles à l'utilisateur",
        responses={200: ChatRoomListSerializer(many=True)}
    ),
    retrieve=extend_schema(
        summary="Détails d'un salon de discussion",
        description="Retourne les détails complets d'un salon de discussion",
        responses={200: ChatRoomSerializer}
    )
)
class ReadOnlyChatRoomViewSet(BaseGenericViewSet, ListModelMixin, RetrieveModelMixin):
    """ViewSet en lecture seule pour les salons de chat."""
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_class = ChatRoomFilter
    pagination_class = ChatRoomPagination
    permission_classes = [AllowAny]
    
    search_fields = ['title', 'event__name']
    ordering_fields = ['timestamp', 'title', 'type', 'visibility', 'status']
    ordering = ['-timestamp']

    def get_queryset(self):
        """Retourne :
        - Tous les salons publics
        - Les salons privés auxquels l'utilisateur a accès via son rôle dans l'organisation
        - Les salons personnels de l'utilisateur
        """
        

        
        # Définit la plage de dates pour les événements
        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)
        
        # Filtre de base pour les dates d'événements
        date_filter = Q(
            # Événements à venir
            Q(event__expiry_date__gte=now) |
            # Événements passés de moins de 7 jours
            Q(
                event__expiry_date__lt=now,
                event__expiry_date__gte=seven_days_ago
            )
        )

        if not self.request.user.is_authenticated:
            # Utilisateur non authentifié : uniquement les salons publics
            return ChatRoom.objects.filter(
                date_filter,
                visibility=ChatRoomVisibilityEnum.PUBLIC.value
            )
        
        # Combine les salons publics et les salons privés accessibles
        # Filtre de base avec les dates
        base_query = ChatRoom.objects.filter(date_filter)
        
        # Filtre pour les salons publics et les salons où l'utilisateur a accès
        # Créer la base du filtre pour les salons publics et privés
        access_filter = Q(visibility=ChatRoomVisibilityEnum.PUBLIC.value)

        if self.request.user.is_authenticated:
            private_rooms = Q(
                visibility=ChatRoomVisibilityEnum.PRIVATE.value,
                event__organization__memberships__user=self.request.user,
            ) | Q(
                visibility=ChatRoomVisibilityEnum.PRIVATE.value,
                event__organization__owner = self.request.user,
            )

            # On ne filtre que les salons qui ont des critères d'accès actifs
            rooms_with_criteria = base_query.filter(
                private_rooms,
                access_criteria__is_active=True
            ).distinct()

            # Pour chaque salon avec des critères, on vérifie si l'utilisateur y a accès
            accessible_room_ids = []
            for room in rooms_with_criteria:
                # Si au moins un des critères est satisfait, l'accès est accordé
                for criteria in room.access_criteria.filter(is_active=True):
                    if criteria.check_user_access(self.request.user):
                        accessible_room_ids.append(room.pk)
                        break

            # On ajoute les salons privés accessibles au filtre
            if accessible_room_ids:
                access_filter |= Q(
                    visibility=ChatRoomVisibilityEnum.PRIVATE.value,
                    pk__in=accessible_room_ids
                )
            
            # On ajoute les salons privés sans critères d'accès
            access_filter |= Q(
                visibility=ChatRoomVisibilityEnum.PRIVATE.value,
                event__organization__memberships__user=self.request.user,
                access_criteria__isnull=True
            )
            # Autoriser l'organisateur (publisher) pour les salons privés sans critères
            access_filter |= Q(
                visibility=ChatRoomVisibilityEnum.PRIVATE.value,
                event__publisher=self.request.user,
                access_criteria__isnull=True
            )
            
            # On ajoute les salons personnels de l'utilisateur
            access_filter |= Q(
                type=ChatRoomTypeEnum.PERSONAL.value,
                subscriptions__user=self.request.user
            )

        return base_query.filter(access_filter).distinct()

    def get_serializer_class(self):
        """Utilise un sérialiseur allégé pour les listes."""
        if self.action == 'list':
            return ChatRoomListSerializer
        return ChatRoomSerializer

    def get_serializer_context(self):
        """
        Ajoute le contexte de la requête au sérialiseur pour permettre
        l'accès aux informations de l'utilisateur connecté.
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @extend_schema(
        description="Liste les salons pour un événement spécifique",
        parameters=[
            OpenApiParameter('event_id', OpenApiTypes.UUID, location=OpenApiParameter.QUERY, required=True,
                             description="ID de l'événement")
        ]
    )
    @action(detail=False, methods=['get'])
    def by_event(self, request):
        event_id = request.query_params.get('event_id')
        if not event_id:
            return Response(
                {"error": "L'ID de l'événement est requis"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        queryset = self.get_queryset().filter(event__pk=event_id)
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Récupération d'un salon personnel",
        description="Récupère un salon personnel entre l'utilisateur courant et un autre utilisateur.",
        parameters=[
            {"name": "interlocutor", "in": "query", "required": True, "type": "string", "format": "uuid", "description": "ID de l'interlocuteur"},
            {"name": "event", "in": "query", "required": True, "type": "string", "format": "uuid", "description": "ID de l'evenement"},
        ],
        responses={200: ChatRoomSerializer}
    )
    @action(detail=False, methods=["get"])
    def get_personal_chat_room(self, request, *args, **kwargs):
        event_pk = request.query_params.get("event")
        interlocutor_pk = request.query_params.get("interlocutor")
        
        if not interlocutor_pk:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.INTERLOCUTOR_REQUIRED),
                code=ErrorEnum.INTERLOCUTOR_REQUIRED.value,
            )
        if not event_pk:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.EVENT_REQUIRED),
                code=ErrorEnum.EVENT_REQUIRED.value,
            )
            
        try:
            interlocutor = User.objects.get(pk=interlocutor_pk)
        except User.DoesNotExist:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.USER_NOT_FOUND),
                code=ErrorEnum.USER_NOT_FOUND.value,
            )
        try: 
            event = Event.objects.get(pk=event_pk)
        except Event.DoesNotExist:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.EVENT_NOT_FOUND),
                code=ErrorEnum.EVENT_NOT_FOUND.value,
            )
        
        # Vérifier qu'il existe un chat room personnel entre ces deux utilisateurs spécifiques
        # Ignorer les abonnements soft-supprimés (subscriptions__is_deleted=False)
        chat_room = ChatRoom.objects.filter(
            type=ChatRoomTypeEnum.PERSONAL.value,
            event=event,
            subscriptions__user=request.user,
            subscriptions__is_deleted=False,
        ).filter(
            subscriptions__user=interlocutor,
            subscriptions__is_deleted=False,
        ).distinct().first()
        
        if not chat_room:
            # Tentative de restauration: si un salon personnel existe mais a été soft-supprimé
            # ou si l'un/les deux abonnements ont été soft-supprimés.
            from apps.chat_rooms.models import ChatRoomSubscription

            # Recherche robuste: identifie le salon qui a des subscriptions pour les 2 utilisateurs
            # en combinant subscriptions actives et soft-supprimées
            rooms_u1_active = set(
                ChatRoomSubscription.objects.filter(
                    user=request.user,
                    chat_room__event=event,
                    chat_room__type=ChatRoomTypeEnum.PERSONAL.value,
                ).values_list("chat_room", flat=True)
            )
            rooms_u1_deleted = set(
                ChatRoomSubscription.deleted_objects.filter(
                    user=request.user,
                    chat_room__event=event,
                    chat_room__type=ChatRoomTypeEnum.PERSONAL.value,
                    is_deleted=True,
                ).values_list("chat_room", flat=True)
            )
            rooms_u2_active = set(
                ChatRoomSubscription.objects.filter(
                    user=interlocutor,
                    chat_room__event=event,
                    chat_room__type=ChatRoomTypeEnum.PERSONAL.value,
                ).values_list("chat_room", flat=True)
            )
            rooms_u2_deleted = set(
                ChatRoomSubscription.deleted_objects.filter(
                    user=interlocutor,
                    chat_room__event=event,
                    chat_room__type=ChatRoomTypeEnum.PERSONAL.value,
                    is_deleted=True,
                ).values_list("chat_room", flat=True)
            )

            common_room_ids = (rooms_u1_active | rooms_u1_deleted) & (rooms_u2_active | rooms_u2_deleted)
            existing = None
            if common_room_ids:
                room_id = next(iter(common_room_ids))
                existing = ChatRoom.deleted_objects.filter(pk=room_id).first() or ChatRoom.objects.filter(pk=room_id).first()

            if existing:
                restored = False
                # Restaure le salon s'il est soft-supprimé
                if getattr(existing, "is_deleted", False):
                    try:
                        existing = existing.restore()
                    except Exception:
                        existing.is_deleted = False
                        if hasattr(existing, "deleted_at"):
                            existing.deleted_at = None
                        existing.save(update_fields=["is_deleted", "deleted_at"] if hasattr(existing, "deleted_at") else ["is_deleted"])
                    restored = True

                # Restaure/assure les abonnements actifs pour les deux utilisateurs
                for target_user in (request.user, interlocutor):
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
                        restored = True
                    else:
                        # Create subscription if none exists
                        ChatRoomSubscription.objects.get_or_create(
                            chat_room=existing,
                            user=target_user,
                            defaults={
                                "role": "ADMIN",
                                "username": target_user.username if getattr(target_user, "username", None) else f"{target_user.first_name} {target_user.last_name}",
                            },
                        )

                if restored:
                    serializer = self.get_serializer(existing)
                    return Response(serializer.data)

            # Aucun salon trouvé ou rien à restaurer
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.PRIVATE_CHAT_ROOM_NOT_FOUND_BETWEEN_USERS),
                code=ErrorEnum.PRIVATE_CHAT_ROOM_NOT_FOUND_BETWEEN_USERS.value,
            )
            
        serializer = self.get_serializer(chat_room)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], name="subscriptions-lite", url_path="subscriptions-lite")
    def subscriptions(self, request, pk=None):
        try:
            # Bypass get_object()/get_queryset filters to avoid 404 for valid room IDs
            chat_room: ChatRoom = ChatRoom.objects.get(pk=pk)
        except ChatRoom.DoesNotExist:
            raise ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.CHAT_ROOM_NOT_FOUND),
                code=ErrorEnum.CHAT_ROOM_NOT_FOUND.value,
            )

        subscriptions = chat_room.subscriptions.all()
        serializer = LightChatRoomSubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data)
        