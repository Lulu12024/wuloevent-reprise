# -*- coding: utf-8 -*-
"""
Tâches Celery pour la mise à jour automatique des tags des salons.
Optimisé pour une application à grande échelle avec des millions d'utilisateurs.
"""

import logging
from celery import shared_task

from apps.chat_rooms.services.tag_service import ChatRoomTagService

logger = logging.getLogger(__name__)

@shared_task(
    name="chat_rooms.update_automatic_tags",
    queue="chat_rooms",
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def update_automatic_tags() -> None:
    """
    Tâche périodique pour mettre à jour les tags automatiques des salons.
    
    Cette tâche est exécutée périodiquement selon l'intervalle défini dans
    TAG_UPDATE_INTERVAL. Elle utilise le ChatRoomTagService pour appliquer
    les règles de tags automatiques.
    
    La tâche est configurée pour :
    - S'exécuter dans une file d'attente dédiée "chat_rooms"
    - Réessayer jusqu'à 3 fois en cas d'échec
    - Attendre 5 minutes entre chaque tentative
    """
    try:
        logger.info("Début de la mise à jour automatique des tags")
        ChatRoomTagService.update_automatic_tags()
        logger.info("Mise à jour automatique des tags terminée avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour automatique des tags: {str(e)}")
        raise  # Celery gérera la nouvelle tentative
