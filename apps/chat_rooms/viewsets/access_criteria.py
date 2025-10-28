"""
Viewset pour la gestion des critères d'accès aux salons de discussion.
"""
import logging

from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from apps.chat_rooms.models import ChatRoomAccessCriteria
from apps.chat_rooms.serializers.access_criteria import ChatRoomAccessCriteriaSerializer
from apps.organizations.models.organizations import Organization
from apps.organizations.permissions import IsOrganizationEventManager
from apps.organizations.mixings import CheckParentPermissionMixin
from apps.utils.utils.baseviews import BaseModelsViewSet

logger = logging.getLogger(__name__)

@extend_schema(
    description='API pour la gestion des critères d\'accès aux salons de discussion.'
)
class ChatRoomAccessCriteriaViewSet(CheckParentPermissionMixin, BaseModelsViewSet):
    """
    Viewset pour gérer les critères d'accès aux salons.
    
    Permet aux gestionnaires d'événements de :
    - Lister les critères d'accès d'un salon
    - Ajouter de nouveaux critères
    - Modifier les critères existants
    - Supprimer des critères
    """
    serializer_default_class = ChatRoomAccessCriteriaSerializer
    parent_queryset = Organization.objects.all()
    parent_lookup_field = 'pk'
    parent_lookup_url_kwarg = 'organization_pk'
    
    permission_classes_by_action = {
        "list": [IsAuthenticated],
        "create": [IsAuthenticated, IsOrganizationEventManager],
        "update": [IsAuthenticated, IsOrganizationEventManager],
        "destroy": [IsAuthenticated, IsOrganizationEventManager],
    }
    
    def get_queryset(self):
        """Retourne les critères d'accès du salon."""
        return ChatRoomAccessCriteria.objects.filter(
            chat_room__event__organization=self.parent_obj
        )
    
    @extend_schema(
        summary='Liste des critères',
        description='Récupère la liste des critères d\'accès du salon.'
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
        
        
    @extend_schema(
        summary='Modification d\'un critère',
        description='Modifie un critère d\'accès existant.',
        request=ChatRoomAccessCriteriaSerializer,
        responses={200: ChatRoomAccessCriteriaSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
        
    @extend_schema(
        summary='Suppression d\'un critère',
        description='Supprime un critère d\'accès du salon.',
        responses={204: None}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
