from django.db import models
from apps.xlib.enums import ChatRoomRolesEnum
from commons.models import AbstractCommonBaseModel


class ChatRoomSubscription(AbstractCommonBaseModel):
    """
    Manages the many-to-many relationship between users and chat rooms.
    
    This model tracks which users are subscribed to which chat rooms and
    includes metadata about the subscription.
    """
    
    user = models.ForeignKey(
        'users.User',
        on_delete=models.DO_NOTHING,
        related_name='chat_room_subscriptions',
        verbose_name="Utilisateur",
        help_text="Utilisateur abonné au salon"
    )
    username = models.CharField(
        verbose_name="Nom d'utilisateur",
        max_length=255,
        null=True,
        blank=True,
        help_text="Nom d'utilisateur de l'utilisateur"
    )
    
    chat_room = models.ForeignKey(
        'chat_rooms.ChatRoom',
        on_delete=models.DO_NOTHING,
        related_name='subscriptions',
        verbose_name="Salon de discussion",
        help_text="Salon de discussion concerné"
    )
    
    joined_at = models.DateTimeField(
        verbose_name="Date d'abonnement",
        null=True,
        blank=True,
        auto_now_add=True,
        help_text="Date à laquelle l'utilisateur a rejoint le salon"
    )
    
    role = models.CharField(
        verbose_name="Role",
        choices=ChatRoomRolesEnum.items(),
        default=ChatRoomRolesEnum.USER.value,
        help_text="Indique le rôle de l'utilisateur dans le salon"
    )
    
    class Meta:
        verbose_name = "Abonnement au salon"
        verbose_name_plural = "Abonnements aux salons"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['chat_room']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['-timestamp']
    
    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.user.username
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.chat_room.title}"
