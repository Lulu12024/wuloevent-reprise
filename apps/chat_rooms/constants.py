# -*- coding: utf-8 -*-
"""
Constants pour le système de tags des salons de discussion.
"""

from enum import Enum
from typing import List, Dict

class ChatRoomTagType(str, Enum):
    """Types de tags pour les salons de discussion."""
    PROMO = "promo"
    IMMINENT = "bientot"
    TRENDING = "tendance"

    @classmethod
    def values(cls) -> List[str]:
        """Retourne la liste des valeurs possibles."""
        return [tag.value for tag in cls]

# Règles pour l'application automatique des tags
TAG_RULES: Dict[str, Dict] = {
    ChatRoomTagType.PROMO.value: {
        "description": "Événements en promotion",
        "auto_remove": True,  # Le tag sera automatiquement retiré quand la promo se termine
    },
    ChatRoomTagType.IMMINENT.value: {
        "description": "Événements qui commencent dans moins de 2 jours",
        "days_threshold": 2,
        "auto_remove": True,
    },
    ChatRoomTagType.TRENDING.value: {
        "description": "Événements avec beaucoup d'engouement",
        "engagement_threshold": 100,  # Nombre d'interactions minimum
        "auto_remove": True,
    }
}

# Intervalle de mise à jour des tags (en secondes)
TAG_UPDATE_INTERVAL = 3600  # 1 heure
