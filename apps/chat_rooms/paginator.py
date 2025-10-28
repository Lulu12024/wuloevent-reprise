# -*- coding: utf-8 -*-
"""
Pagination pour les salons de discussion.
Optimisé pour une application à grande échelle avec des millions d'utilisateurs.
"""

from rest_framework.pagination import PageNumberPagination


class ChatRoomPagination(PageNumberPagination):
    """
    Pagination optimisée pour les salons de discussion.
    
    Caractéristiques :
    1. Taille de page configurable via paramètre
    2. Limite maximale de taille de page pour éviter la surcharge
    3. Paramètre de page personnalisé pour une meilleure UX
    4. Réponse formatée avec métadonnées utiles
    """
    
    page_size = 20  # Taille par défaut
    page_size_query_param = 'page_size'  # Permet de personnaliser la taille via ?page_size=X
    max_page_size = 100  # Limite maximale pour éviter les abus
    page_query_param = 'p'  # Utilise ?p=X au lieu de ?page=X

    def get_paginated_response(self, data):
        return super().get_paginated_response(data)

