"""
Sérialiseurs pour les abonnements aux salons de discussion.
"""
from rest_framework import serializers

from apps.chat_rooms.models import ChatRoomSubscription
from apps.chat_rooms.serializers.chat_room import ChatRoomSerializer
from apps.users.serializers import UserSerializerLight


class ChatRoomSubscriptionListSerializer(serializers.ModelSerializer):
    """
    Sérialiseur pour les abonnements aux salons.
    """
     
    class Meta:
        model = ChatRoomSubscription
        fields = [
            'pk', 'username', 'role',
            'joined_at', 'timestamp', 'updated'
        ]
        read_only_fields = [
            'pk', 'username', 'role',
            'joined_at', 'timestamp', 'updated'
        ]
class ChatRoomSubscriptionSerializer(serializers.ModelSerializer):
    """
    Sérialiseur pour les abonnements aux salons.
    """
    chat_room = ChatRoomSerializer(read_only=True)
    
    class Meta:
        model = ChatRoomSubscription
        fields = [
            'pk', 'chat_room', 'username', 'role',
            'joined_at', 'timestamp', 'updated'
        ]
        read_only_fields = [
            'pk', 'chat_room', 'username', 'role',
            'joined_at', 'timestamp', 'updated'
        ]
class LightChatRoomSubscriptionSerializer(serializers.ModelSerializer):
    user = UserSerializerLight(read_only=True)
    class Meta:
        model = ChatRoomSubscription
        fields = [
            'pk', 'user', 'chat_room', 'username', 'role',
        ]
        read_only_fields = [
            'pk', 'user', 'chat_room', 'username', 'role',
        ]

class ChatRoomSubscriptionCreateSerializer(serializers.ModelSerializer):
    """
    Sérialiseur pour la création d'abonnements aux salons.
    Définit explicitement les champs d'entrée attendus.
    """
    username = serializers.CharField(required=False, help_text="Nom d'utilisateur à utiliser dans le salon. Si non fourni, le nom d'utilisateur du compte sera utilisé.")
    
    class Meta:
        model = ChatRoomSubscription
        fields = ['username']
