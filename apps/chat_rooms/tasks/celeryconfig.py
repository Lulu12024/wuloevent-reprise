# -*- coding: utf-8 -*-
"""
Configuration Celery pour les tâches des salons de discussion.
Optimisé pour une application à grande échelle avec des millions d'utilisateurs.
"""

from apps.chat_rooms.constants import TAG_UPDATE_INTERVAL

# Configuration des tâches périodiques
beat_schedule = {
    'update-chat-room-tags': {
        'task': 'chat_rooms.update_automatic_tags',
        'schedule': TAG_UPDATE_INTERVAL,  # Exécution toutes les heures
        'options': {
            'queue': 'chat_rooms',
            'expires': TAG_UPDATE_INTERVAL * 2  # La tâche expire après 2 intervalles
        }
    }
}

# Configuration des files d'attente
task_routes = {
    'chat_rooms.*': {'queue': 'chat_rooms'}
}

# Optimisations pour une grande échelle
task_acks_late = True  # Confirmation tardive pour une meilleure performance
task_reject_on_worker_lost = True  # Réexécution des tâches si le worker meurt
worker_prefetch_multiplier = 1  # Évite la surcharge des workers
task_default_rate_limit = '10000/m'  # Limite le taux d'exécution pour éviter la surcharge
