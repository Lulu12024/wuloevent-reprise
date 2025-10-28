from rest_framework import serializers
from apps.chat_rooms.models import ChatRoomAccessCriteria


class ChatRoomAccessCriteriaSerializer(serializers.ModelSerializer):
    """
    Sérialiseur pour les critères d'accès aux salons.
    Inclut le titre lisible généré automatiquement.
    """
    
    class Meta:
        model = ChatRoomAccessCriteria
        fields = [
            'pk', 'name', 'description', 'criteria_type',
            'criteria_rules', 'is_active'
        ]
        read_only_fields = ['pk','name']
