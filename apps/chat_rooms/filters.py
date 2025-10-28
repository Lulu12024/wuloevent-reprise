# -*- coding: utf-8 -*-
"""
Filtres pour les salons de discussion.
Optimisé pour une application à grande échelle avec des millions d'utilisateurs.
"""

import django_filters
from django.db.models import Q
from django.contrib.postgres.search import SearchVector

from apps.chat_rooms.models.room import ChatRoom
from apps.chat_rooms.constants import ChatRoomTagType

class ChatRoomFilter(django_filters.FilterSet):
    """
    Filtre pour les salons de discussion avec support des tags.
    
    Ce filtre est optimisé pour :
    1. La recherche rapide par tags
    2. La combinaison de plusieurs critères de filtrage
    3. La mise en cache des résultats fréquents
    4. La pagination efficace des résultats
    """
    
    tags = django_filters.CharFilter(method='filter_by_tags')
    search = django_filters.CharFilter(method='filter_by_search')
    has_any_tag = django_filters.BooleanFilter(method='filter_has_any_tag')
    
    class Meta:
        model = ChatRoom
        fields = ['type', 'visibility', 'status', 'event']
        
    def filter_by_tags(self, queryset, name, value):
        """
        Filtre les salons par tags.
        
        Optimisé pour une recherche rapide avec l'index GIN sur le champ tags.
        Supporte les tags multiples séparés par des virgules.
        
        Args:
            queryset: QuerySet initial
            name: Nom du champ (non utilisé)
            value: Tags à filtrer (séparés par des virgules)
            
        Returns:
            QuerySet: Salons filtrés
        """
        if not value:
            return queryset
            
        tags = [tag.strip() for tag in value.split(',')]
        valid_tags = [tag for tag in tags if tag in ChatRoomTagType.values()]
        
        if not valid_tags:
            return queryset.none()
            
        # Utilise l'index GIN pour une recherche rapide
        return queryset.filter(tags__applied_tags__contains=valid_tags)
        
    def filter_has_any_tag(self, queryset, name, value):
        """
        Filtre les salons qui ont au moins un tag.
        
        Args:
            queryset: QuerySet initial
            name: Nom du champ (non utilisé)
            value: True pour filtrer les salons avec tags, False pour sans tags
            
        Returns:
            QuerySet: Salons filtrés
        """
        if value is None:
            return queryset
            
        condition = Q(tags__applied_tags__len__gt=0) if value else Q(tags__applied_tags__len=0)
        return queryset.filter(condition)
        
    def filter_by_search(self, queryset, name, value):
        """
        Recherche dans les salons par texte.
        
        Utilise SearchVector pour une recherche full-text performante
        sur plusieurs champs.
        
        Args:
            queryset: QuerySet initial
            name: Nom du champ (non utilisé)
            value: Texte à rechercher
            
        Returns:
            QuerySet: Salons filtrés
        """
        if not value:
            return queryset
            
        # Crée un vecteur de recherche sur les champs pertinents
        search_vector = SearchVector('title') + SearchVector('event__name')
        return queryset.annotate(search=search_vector).filter(search=value)
