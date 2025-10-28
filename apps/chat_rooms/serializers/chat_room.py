from rest_framework import serializers
 
from apps.chat_rooms.models import ChatRoom, ChatRoomSubscription
from apps.events.serializers import LightEventSerializer
from apps.chat_rooms.serializers.access_criteria import ChatRoomAccessCriteriaSerializer
from apps.xlib.error_util import ErrorUtil, ErrorEnum

class ChatRoomSerializer(serializers.ModelSerializer):
    """
    Sérialiseur principal pour les salons de discussion.
    Optimisé pour :
    1. La pagination efficace
    2. Le chargement sélectif des relations
    3. La validation des données
    4. La gestion des permissions
    """
    access_criteria = ChatRoomAccessCriteriaSerializer(
        many=True,
        read_only=True
    )
    event = LightEventSerializer(read_only=True)
    event_id = serializers.UUIDField(write_only=True)
    current_tags = serializers.ListField(
        child=serializers.CharField(),
        read_only=True
    )
    
    class Meta:
        model = ChatRoom
        fields = [
            'pk', 'title', 'type', 'visibility', 'status',
            'event', 'event_id', 'access_criteria', 'current_tags',
            'timestamp', 'updated'
        ]
        read_only_fields = ['pk', 'timestamp', 'updated']
    
    def validate_event_id(self, value):
        """Valide que l'événement existe et est accessible."""
        from apps.events.models import Event
        try:
            event = Event.objects.get(pk=value)
           
            if not event.have_passed_validation:
                raise serializers.ValidationError(
                    ErrorUtil.get_error_detail(ErrorEnum.EVENT_UNDERGOING_VALIDATION),
                    code=ErrorEnum.EVENT_UNDERGOING_VALIDATION.value,
                )
            if not event.valid:
                raise serializers.ValidationError(
                    ErrorUtil.get_error_detail(ErrorEnum.INVALID_EVENT_DATA),
                    code=ErrorEnum.INVALID_EVENT_DATA.value,
                )
            return event
        except Event.DoesNotExist:
            raise serializers.ValidationError(
                ErrorUtil.get_error_detail(ErrorEnum.RESOURCE_NOT_FOUND),
                code=ErrorEnum.RESOURCE_NOT_FOUND.value,
            )
    def create(self, validated_data):
        event  = validated_data.pop("event_id")
        validated_data["event_id"]=event.pk
        return super().create(validated_data)


class ChatRoomListSerializer(ChatRoomSerializer):
    """
    Version allégée du sérialiseur pour les listes de salons.
    Optimisé pour les requêtes de liste avec pagination.
    
    Inclut les informations d'abonnement uniquement pour les utilisateurs connectés.
    """
    from apps.chat_rooms.serializers.subscription import ChatRoomSubscriptionListSerializer

    event = LightEventSerializer()
    subscription = serializers.SerializerMethodField()
    subscriptions = ChatRoomSubscriptionListSerializer(many=True)
    
    class Meta(ChatRoomSerializer.Meta):
        fields = [
            'pk', 'title', 'type', 'visibility', 'status',
            'event', 'current_tags', 'timestamp', 'subscription','subscriptions'
        ]
    
    def get_subscription(self, obj):
        from apps.chat_rooms.serializers.subscription import ChatRoomSubscriptionListSerializer

        """
        Récupère les informations d'abonnement de l'utilisateur actuel au salon.
        Retourne None si l'utilisateur n'est pas connecté ou n'est pas abonné.
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
            
        try:
            subscription = ChatRoomSubscription.objects.get(
                user=request.user,
                chat_room=obj
            )
            return ChatRoomSubscriptionListSerializer(subscription).data
        except ChatRoomSubscription.DoesNotExist:
            return None

