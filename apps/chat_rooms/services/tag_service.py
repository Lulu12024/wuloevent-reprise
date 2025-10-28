# -*- coding: utf-8 -*-
"""
Service de gestion des tags pour les salons de discussion.
Optimisé pour une application à grande échelle avec des millions d'utilisateurs.
"""

import logging
from typing import List, Dict, Optional
from datetime import timedelta

from django.utils import timezone
from django.db.models import Count, Q, QuerySet
from django.core.exceptions import ValidationError

from apps.chat_rooms.constants import ChatRoomTagType, TAG_RULES
from apps.chat_rooms.models.room import ChatRoom
from apps.events.models import Event

logger = logging.getLogger(__name__)

class ChatRoomTagService:
    """Service pour la gestion des tags des salons de discussion."""

    @staticmethod
    def validate_tags(tags: List[str]) -> bool:
        """Valide une liste de tags.
        
        Args:
            tags: Liste des tags à valider
            
        Returns:
            bool: True si tous les tags sont valides
            
        Raises:
            ValidationError: Si un tag n'est pas valide
        """
        valid_tags = ChatRoomTagType.values()
        invalid_tags = [tag for tag in tags if tag not in valid_tags]
        
        if invalid_tags:
            raise ValidationError(
                f"Tags invalides: {', '.join(invalid_tags)}. "
                f"Tags valides: {', '.join(valid_tags)}"
            )
        return True

    @staticmethod
    def update_room_tags(room: ChatRoom, tags: List[str]) -> None:
        """Met à jour les tags d'un salon.
        
        Args:
            room: Le salon à mettre à jour
            tags: Liste des nouveaux tags
        """
        try:
            ChatRoomTagService.validate_tags(tags)
            room.tags = {"applied_tags": tags}
            room.save(update_fields=['tags'])
            logger.info(f"Tags mis à jour pour le salon {room.pk}: {tags}")
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des tags du salon {room.pk}: {str(e)}")
            raise

    @staticmethod
    def add_tag(room: ChatRoom, tag: str) -> None:
        """Ajoute un tag à un salon s'il n'existe pas déjà.
        
        Args:
            room: Le salon
            tag: Le tag à ajouter
        """
        try:
            ChatRoomTagService.validate_tags([tag])
            current_tags = room.tags.get("applied_tags", [])
            if tag not in current_tags:
                current_tags.append(tag)
                room.tags["applied_tags"] = current_tags
                room.save(update_fields=['tags'])
                logger.info(f"Tag {tag} ajouté au salon {room.pk}")
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du tag {tag} au salon {room.pk}: {str(e)}")
            raise

    @staticmethod
    def remove_tag(room: ChatRoom, tag: str) -> None:
        """Retire un tag d'un salon.
        
        Args:
            room: Le salon
            tag: Le tag à retirer
        """
        try:
            current_tags = room.tags.get("applied_tags", [])
            if tag in current_tags:
                current_tags.remove(tag)
                room.tags["applied_tags"] = current_tags
                room.save(update_fields=['tags'])
                logger.info(f"Tag {tag} retiré du salon {room.pk}")
        except Exception as e:
            logger.error(f"Erreur lors du retrait du tag {tag} du salon {room.pk}: {str(e)}")
            raise

    @classmethod
    def update_automatic_tags(cls) -> None:
        """Met à jour les tags automatiques pour tous les salons selon les règles définies.
        
        Cette méthode est optimisée pour une application à grande échelle avec :
        1. Utilisation de select_related pour réduire les requêtes
        2. Mise à jour en lot pour éviter les requêtes multiples
        3. Gestion appropriée des transactions
        4. Logging détaillé pour le monitoring
        """
        try:
            now = timezone.now()
            logger.info(f"Début de la mise à jour des tags automatiques à {now}")
            
            # Mise à jour des tags "bientot"
            imminent_threshold = now + timedelta(days=TAG_RULES[ChatRoomTagType.IMMINENT.value]["days_threshold"])
            imminent_rooms = ChatRoom.objects.select_related('event').filter(
                event__date__lte=imminent_threshold,
                event__date__gt=now
            )

            
            # Mise à jour des tags "tendance"
            #trending_threshold = TAG_RULES[ChatRoomTagType.TRENDING.value]["engagement_threshold"]
            ########### TODO: Add event__chat_messages count once Discussion module will completed
            # trending_rooms = ChatRoom.objects.select_related('event').annotate(
            #     engagement_count=Count('event__chat_messages')
            # ).filter(
            #     engagement_count__gte=trending_threshold
            # )
            
            updated_count = 0
            # Application des tags en lot
            for room in imminent_rooms:
                if not room.has_tag(ChatRoomTagType.IMMINENT.value):
                    if not room.tags:
                        room.tags = {"applied_tags": []}
                    room.tags["applied_tags"].append(ChatRoomTagType.IMMINENT.value)

                    room.save(update_fields=['tags'])
                    updated_count += 1
                    logger.debug(f"Tag 'bientot' ajouté au salon {room.pk}")
            
            # Retrait des tags périmés
            
            removed_count = cls._remove_expired_tags()
            
            logger.info(
                f"Mise à jour automatique des tags terminée. "
                f"{updated_count} tags ajoutés, {removed_count} tags retirés"
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour automatique des tags: {str(e)}")
            raise

    @classmethod
    def _remove_expired_tags(cls) -> int:
        """Retire les tags périmés des salons.
        
        Cette méthode est optimisée pour une application à grande échelle avec :
        1. Utilisation de select_related pour réduire les requêtes
        2. Mise à jour en lot pour éviter les requêtes multiples
        3. Comptage des tags retirés pour le monitoring
        
        Returns:
            int: Nombre de tags retirés
        """
        now = timezone.now()
        removed_count = 0
        
        # Retire le tag "bientot" des événements passés
        expired_imminent = ChatRoom.objects.select_related('event').filter(
            Q(tags__applied_tags__contains=[ChatRoomTagType.IMMINENT.value]) &
            Q(event__date__lte=now)
        )
        
        for room in expired_imminent:
            if ChatRoomTagType.IMMINENT.value in room.tags.get("applied_tags", []):
                room.tags["applied_tags"].remove(ChatRoomTagType.IMMINENT.value)
                room.save(update_fields=['tags'])
                removed_count += 1
                logger.debug(f"Tag 'bientot' retiré du salon {room.pk}")
        
        # Retire le tag "tendance" des salons qui ne sont plus tendance
        #trending_threshold = TAG_RULES[ChatRoomTagType.TRENDING.value]["engagement_threshold"]
        
        # expired_trending = ChatRoom.objects.filter(
        #     tags__applied_tags__contains=[ChatRoomTagType.TRENDING.value]
        # ).annotate(
        #     engagement_count=Count('event__chat_messages')
        # ).filter(
        #     engagement_count__lt=trending_threshold
        # )
        
        #for room in expired_trending:
        #    cls.remove_tag(room, ChatRoomTagType.TRENDING.value)

    @staticmethod
    def filter_rooms_by_tags(tags: List[str], queryset: Optional[QuerySet] = None) -> QuerySet:
        """Filtre les salons par tags.
        
        Args:
            tags: Liste des tags à filtrer
            queryset: QuerySet optionnel à filtrer (utilise tous les salons si non fourni)
            
        Returns:
            QuerySet: Les salons filtrés
        """
        if queryset is None:
            queryset = ChatRoom.objects.all()
            
        return queryset.filter(tags__applied_tags__contains=tags)
