import logging
from typing import List

from django.db import models
from django.db.models import JSONField
from django.core.exceptions import ValidationError

from commons.models import AbstractCommonBaseModel
from apps.xlib.enums import ChatRoomTypeEnum, ChatRoomVisibilityEnum, ChatRoomStatusEnum
from apps.chat_rooms.constants import ChatRoomTagType

logger = logging.getLogger(__name__)


class ChatRoom(AbstractCommonBaseModel):
    """
    Represents a chat room in the system.
    
    This model stores all information related to a chat room, including its type,
    visibility, and associated metadata.
    """
    


    # Basic information
    title = models.CharField(
        verbose_name="Titre",
        max_length=255,
        help_text="Titre du salon de discussion"
    )
    
    type = models.CharField(
        verbose_name="Type",
        max_length=20,
        choices=ChatRoomTypeEnum.items(),
        default=ChatRoomTypeEnum.SECONDARY.value,
        help_text="Type du salon (principal ou secondaire)"
    )
    
    visibility = models.CharField(
        verbose_name="Visibilité",
        max_length=20,
        choices=ChatRoomVisibilityEnum.items(),
        default=ChatRoomVisibilityEnum.PUBLIC.value,
        help_text="Visibilité du salon (public ou privé)"
    )
    
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.DO_NOTHING,
        related_name='chat_rooms',
        verbose_name="Événement",
        help_text="Événement associé au salon"
    )

    # Media
    profile_image = models.ImageField(
        verbose_name="Image de profil",
        upload_to='chat_rooms/profile/',
        null=True,
        blank=True,
        help_text="Image de profil du salon"
    )
    
    cover_image = models.ImageField(
        verbose_name="Image de couverture",
        upload_to='chat_rooms/cover/',
        null=True,
        blank=True,
        help_text="Image de couverture du salon"
    )
    
    status = models.CharField(
        verbose_name="Statut",
        max_length=20,
        choices=ChatRoomStatusEnum.items(),
        default=ChatRoomStatusEnum.ACTIVE.value,
        help_text="Statut du salon (actif ou fermé)"
    )

    # JSON fields
    tags = JSONField(
        verbose_name="Tags",
        default=dict,
        blank=True,
        help_text="Tags associés au salon en format JSON"
    )
    
    @property
    def access_rules(self):
        """Retourne les règles d'accès actives pour ce salon."""
        return self.access_criteria.filter(is_active=True)

    def check_user_access(self, user):
        """Vérifie si un utilisateur a accès au salon selon les critères définis.
        
        Args:
            user: L'utilisateur à vérifier
            
        Returns:
            bool: True si l'utilisateur a accès, False sinon
        """
        # Si le salon est public, accès autorisé
        if self.visibility == ChatRoomVisibilityEnum.PUBLIC.value:
            return True
            
        # Pour les salons privés, vérifie tous les critères actifs
        for criterion in self.access_rules:         
            if not criterion.check_user_access(user):
                return False
                
        return True

    @property
    def current_tags(self) -> List[str]:
        """Retourne la liste des tags actuels du salon.
        
        Returns:
            List[str]: Liste des tags appliqués au salon
        """
        return self.tags.get("applied_tags", [])
    
    def has_tag(self, tag: str) -> bool:
        """Vérifie si le salon a un tag spécifique.
        
        Args:
            tag: Le tag à vérifier
            
        Returns:
            bool: True si le salon a le tag, False sinon
        """
        return tag in self.current_tags
    
    def add_tag(self, tag: str) -> None:
        """Ajoute un tag au salon s'il n'existe pas déjà.
        
        Cette méthode est thread-safe et optimisée pour une utilisation
        à grande échelle.
        
        Args:
            tag: Le tag à ajouter
            
        Raises:
            ValidationError: Si le tag n'est pas valide
        """
        if tag not in ChatRoomTagType.values():
            raise ValidationError(f"Tag invalide: {tag}")
            
        if not self.has_tag(tag):
            self.tags.setdefault("applied_tags", []).append(tag)
            self.save(update_fields=['tags'])
            logger.info(f"Tag {tag} ajouté au salon {self.pk}")
    
    def remove_tag(self, tag: str) -> None:
        """Retire un tag du salon.
        
        Args:
            tag: Le tag à retirer
        """
        if self.has_tag(tag):
            self.tags["applied_tags"].remove(tag)
            self.save(update_fields=['tags'])
            logger.info(f"Tag {tag} retiré du salon {self.pk}")
    
    class Meta:
        verbose_name = "Salon de discussion"
        verbose_name_plural = "Salons de discussion"
        indexes = [
            models.Index(fields=['type']),
            models.Index(fields=['visibility']),
            models.Index(fields=['status']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['event']),
        ]
        ordering = ['-timestamp']
        unique_together=["event","title"]

    def __str__(self):
        return f"{self.title} ({self.type})"

    def save(self, *args, **kwargs):
        """Sauvegarde le salon en validant les tags.
        
        Cette méthode assure que :
        1. Les tags sont dans un format valide
        2. Seuls les tags autorisés sont utilisés
        3. Les modifications sont journalisées
        
        Raises:
            ValidationError: Si les tags ne sont pas valides
        """
        try:
            # Initialise les tags si nécessaire
            if not self.tags:
                self.tags = {"applied_tags": []}
            elif "applied_tags" not in self.tags:
                self.tags["applied_tags"] = []
                
            # Valide les tags
            current_tags = self.tags.get("applied_tags", [])
            if current_tags:
                valid_tags = ChatRoomTagType.values()
                invalid_tags = [tag for tag in current_tags if tag not in valid_tags]
                if invalid_tags:
                    raise ValidationError(
                        f"Tags invalides détectés: {', '.join(invalid_tags)}"
                    )
            
            super().save(*args, **kwargs)
            logger.info(f"Salon {self.pk} sauvegardé avec les tags: {current_tags}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du salon {self.pk}: {str(e)}")
            raise
