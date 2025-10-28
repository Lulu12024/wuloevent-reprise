from django.db import models

from commons.models import AbstractCommonBaseModel
from apps.xlib.enums import NotificationLevelEnum

class ChatRoomPreference(AbstractCommonBaseModel):
    """
    Stores user preferences for specific chat rooms.
    
    This model allows users to customize their experience for each chat room
    they are part of, including notification settings and display preferences.
    """
    
    user = models.ForeignKey(
        'users.User',
        on_delete=models.DO_NOTHING,
        related_name='chat_room_preferences',
        verbose_name="Utilisateur",
        help_text="Utilisateur concerné par les préférences"
    )
    
    chat_room = models.ForeignKey(
        'chat_rooms.ChatRoom',
        on_delete=models.DO_NOTHING,
        related_name='user_preferences',
        verbose_name="Salon de discussion",
        help_text="Salon de discussion concerné"
    )
    
    custom_name = models.CharField(
        verbose_name="Nom personnalisé",
        max_length=255,
        null=True,
        blank=True,
        help_text="Nom personnalisé du salon pour cet utilisateur"
    )
    
    is_muted = models.BooleanField(
        verbose_name="Mise en sourdine",
        default=False,
        help_text="Indique si le salon est en sourdine pour cet utilisateur"
    )
    
    notification_level = models.CharField(
        verbose_name="Niveau de notification",
        max_length=20,
        choices=NotificationLevelEnum.items(),
        default=NotificationLevelEnum.ALL.value,
        help_text="Niveau de notification pour ce salon"
    )
    
    last_read_at = models.DateTimeField(
        verbose_name="Dernière lecture",
        null=True,
        blank=True,
        help_text="Dernière fois que l'utilisateur a lu les messages du salon"
    )

    class Meta:
        verbose_name = "Préférence de salon"
        verbose_name_plural = "Préférences de salon"
        unique_together = ['user', 'chat_room']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['chat_room']),
            models.Index(fields=['notification_level']),
        ]

    def __str__(self):
        return f"Préférences de {self.user.username} pour {self.chat_room.title}"
