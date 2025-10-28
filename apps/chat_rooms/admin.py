from django.contrib import admin

# Register your models here.

from apps.chat_rooms.models import ChatRoom, ChatRoomAccessCriteria, ChatRoomSubscription, ChatRoomPreference
from commons.admin import BaseModelAdmin

@admin.register(ChatRoom)
class ChatRoomAdmin(BaseModelAdmin):
    pass

@admin.register(ChatRoomSubscription)
class ChatRoomSubscriptionAdmin(BaseModelAdmin):
    pass

@admin.register(ChatRoomPreference)
class ChatRoomPreferenceAdmin(BaseModelAdmin):
    pass

@admin.register(ChatRoomAccessCriteria)
class ChatRoomAccessCriteriaAdmin(BaseModelAdmin):
    pass
