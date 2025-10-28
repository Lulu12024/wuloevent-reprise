from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter

from apps.chat_rooms.viewsets.chat_room_read_only import ReadOnlyChatRoomViewSet
from apps.chat_rooms.viewsets.subscription import ChatRoomSubscriptionViewSet

# Router principal
router = DefaultRouter()
router.register(r'chat-rooms', ReadOnlyChatRoomViewSet, basename='chatroom')

# Router imbriqué pour les abonnements
chat_room_router = NestedSimpleRouter(
    router, r"chat-rooms", lookup='chat_room'
)
chat_room_router.register(r'subscriptions', ChatRoomSubscriptionViewSet, basename='chat-room-subscriptions')

# Combine les URLs
urls_patterns = router.urls
