# -*- coding: utf-8 -*-
"""
Service de génération de titres pour les critères d'accès aux salons.
Optimisé pour une application à grande échelle avec des millions d'utilisateurs.
"""

import logging
from typing import Dict

from django.utils.translation import gettext_lazy as _
from django.core.cache import cache

from apps.xlib.enums import AccessCriteriaTypeEnum
from apps.chat_rooms.models.access_criteria import ChatRoomAccessCriteria
from apps.events.models import Ticket

logger = logging.getLogger(__name__)

class AccessTitleService:
    """
    Service pour générer des titres lisibles pour les critères d'accès.
    
    Ce service est optimisé pour :
    1. La mise en cache des titres fréquemment utilisés
    2. La génération efficace de titres pour de multiples critères
    3. Le support multilingue via gettext
    4. La gestion des erreurs et le logging
    """
    
    # Clé de cache pour les titres générés
    CACHE_KEY_PREFIX = "access_title:"
    CACHE_TIMEOUT = 3600  # 1 heure
    
    @classmethod
    def generate_title(cls, criteria: ChatRoomAccessCriteria) -> str:
        """
        Génère un titre lisible pour un critère d'accès.
        
        Cette méthode utilise le cache pour éviter de régénérer
        les titres fréquemment utilisés.
        
        Args:
            criteria: Le critère d'accès
            
        Returns:
            str: Titre lisible du critère
        """
        cache_key = f"{cls.CACHE_KEY_PREFIX}{criteria.pk}"
        cached_title = cache.get(cache_key)
        
        if cached_title:
            return cached_title
            
        try:
            title = cls._generate_title_by_type(criteria)
            cache.set(cache_key, title, cls.CACHE_TIMEOUT)
            return title
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du titre pour {criteria}: {str(e)}")
            return _("Réservé aux utilisateurs autorisés")
    
    @classmethod
    def _generate_title_by_type(cls, criteria: ChatRoomAccessCriteria) -> str:
        """
        Génère un titre en fonction du type de critère.
        
        Args:
            criteria: Le critère d'accès
            
        Returns:
            str: Titre généré
        """
        if criteria.criteria_type == AccessCriteriaTypeEnum.ROLE.value:
            return cls._generate_role_title(criteria.criteria_rules)
            
        elif criteria.criteria_type == AccessCriteriaTypeEnum.EVENT_TICKET.value:
            return cls._generate_ticket_title(criteria.criteria_rules)
               
        return _("Réservé aux utilisateurs autorisés")
    
    @staticmethod
    def _generate_role_title(rules: Dict) -> str:
        """Génère un titre pour les critères basés sur les rôles."""
        roles = rules.get('required_roles', [])
        if not roles:
            return _("Réservé aux utilisateurs autorisés")
            
        roles_str = ", ".join(roles)
        return _("Réservé aux utilisateurs avec le(s) rôle(s) : %(roles)s") % {"roles": roles_str}
    
    @staticmethod
    def _generate_ticket_title(rules: Dict) -> str:
        """Génère un titre pour les critères basés sur les tickets."""
        ticket_ids = rules.get('required_tickets', [])
        if not ticket_ids:
            return _("Réservé aux détenteurs de billets")
            
        try:
            tickets = Ticket.objects.filter(pk__in=ticket_ids)
            ticket_names = [ticket.name for ticket in tickets]
            tickets_str = ", ".join(ticket_names)
            return _("Réservé aux détenteurs des billets : %(tickets)s") % {"tickets": tickets_str}
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des tickets {ticket_ids}: {str(e)}")
            return _("Réservé aux détenteurs de billets")
    