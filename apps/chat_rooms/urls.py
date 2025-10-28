# -*- coding: utf-8 -*-
"""
Configuration des URLs pour l'API des salons de discussion.
Optimisé pour une application à grande échelle avec des millions d'utilisateurs.
"""
from apps.chat_rooms.router import router, chat_room_router


urlpatterns = []

# Ajoute les URLs du router principal et du router imbriqué
urlpatterns += router.urls
urlpatterns += chat_room_router.urls
