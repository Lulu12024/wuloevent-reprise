import logging
from uuid import UUID

from django.db import models
from django.db.models import JSONField, Q
from django.utils import timezone

from commons.models import AbstractCommonBaseModel
from apps.events.models import Ticket, ETicket
from apps.xlib.enums import AccessCriteriaTypeEnum, OrderStatusEnum
from rest_framework.validators import ValidationError
logger = logging.getLogger(__name__)


class ChatRoomAccessCriteria(AbstractCommonBaseModel):
    """
    Defines access criteria for private chat rooms.
    
    This model allows for fine-grained control over who can access private chat rooms
    based on various criteria such as user roles, attributes, or other conditions.
    """
    
    chat_room = models.ForeignKey(
        'chat_rooms.ChatRoom',
        on_delete=models.DO_NOTHING,
        related_name='access_criteria',
        verbose_name="Salon de discussion",
        help_text="Salon de discussion concerné"
    )
    
    name = models.CharField(
        verbose_name="Nom",
        max_length=255,
        help_text="Nom du critère d'accès"
    )
    
    description = models.TextField(
        verbose_name="Description",
        blank=True,
        help_text="Description détaillée du critère d'accès"
    )
    
    criteria_type = models.CharField(
        verbose_name="Type de critère",
        max_length=50,
        choices=AccessCriteriaTypeEnum.items(),
        help_text="Type de critère d'accès"
    )
    """
    {
        "required_roles": ["role1", "role2"],
        "required_tickets": ["type","type2"]
    }
    """
    criteria_rules = JSONField(
        verbose_name="Règles du critère",
        help_text="Règles définissant le critère d'accès en format JSON"
    )
    
    is_active = models.BooleanField(
        verbose_name="Actif",
        default=True,
        help_text="Indique si ce critère est actuellement actif"
    )
    
    class Meta:
        verbose_name = "Critère d'accès"
        verbose_name_plural = "Critères d'accès"
        indexes = [
            models.Index(fields=['chat_room']),
            models.Index(fields=['criteria_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['chat_room', 'name']

    def readable_title(self) -> str:
        """Génère un titre lisible pour ce critère d'accès.
        
        Cette propriété utilise le AccessTitleService pour générer un titre
        lisible et compréhensible pour les utilisateurs. Le titre est mis en cache
        pour optimiser les performances.
        
        Returns:
            str: Titre lisible du critère d'accès
        """
        from apps.chat_rooms.services.access_title_service import AccessTitleService
        return AccessTitleService.generate_title(self)
    
    def __str__(self):
        return self.name

    def validate_criteria_rules(self):
        """
        Valide que les règles de critères suivent le schéma attendu.
        
        Cette méthode est appelée avant la sauvegarde pour garantir l'intégrité
        des données. Elle vérifie que les règles sont correctement formatées
        selon le type de critère.
        
        Raises:
            ValidationError: Si les règles ne sont pas valides
        """
        from django.core.exceptions import ValidationError
        
        if not isinstance(self.criteria_rules, dict):
            raise ValidationError("Les règles doivent être un dictionnaire JSON")
            
        try:
            if self.criteria_type == AccessCriteriaTypeEnum.ROLE.value:
                required_roles = self.criteria_rules.get('required_roles')
                if not isinstance(required_roles, list) or not required_roles:
                    raise ValidationError("'required_roles' doit être une liste non vide")
                
            elif self.criteria_type == AccessCriteriaTypeEnum.EVENT_TICKET.value:
                required_tickets = self.criteria_rules.get('required_tickets')
                if not isinstance(required_tickets, list) or not required_tickets:
                    raise ValidationError("'required_tickets' doit être une liste non vide d'IDs de tickets")
                    
                # Vérifie que tous les tickets existent
                # Convertit les IDs en UUID pour la requête
                try:
                    # Si l'ID est déjà un UUID, le convertit en string
                    ticket_ids = []
                    for tid in required_tickets:
                        if isinstance(tid, UUID):
                            ticket_ids.append(tid)
                        else:
                            try:
                                ticket_ids.append(UUID(str(tid)))
                            except (ValueError, AttributeError, TypeError):
                                raise ValidationError(
                                    f"L'ID de ticket '{tid}' n'est pas un UUID valide"
                                )
                except ValidationError:
                    raise
                except Exception as e:
                    raise ValidationError(
                        "Les IDs de tickets doivent être des UUIDs valides"
                    ) from e
                
                # Optimisation : utilise une seule requête pour vérifier l'existence des tickets
                # avec un index sur le champ pk
                existing_tickets = set(str(pk) for pk in Ticket.objects.filter(
                    pk__in=ticket_ids
                ).values_list('pk', flat=True))
                
                # Vérifie que tous les tickets requis existent
                invalid_tickets = set(str(tid) for tid in ticket_ids) - existing_tickets
                if invalid_tickets:
                    raise ValidationError(
                        f"Les tickets suivants n'existent pas : {', '.join(invalid_tickets)}"
                    )
        except ValidationError:
            raise
        except Exception as e:
            # Log l'erreur pour le débogage mais ne divulgue pas les détails techniques
            # dans le message d'erreur pour des raisons de sécurité
            logger.error(f"Erreur lors de la validation des règles: {str(e)}")
            raise ValidationError("Erreur lors de la validation des règles")

    def save(self, *args, **kwargs):
        """Surcharge de la méthode save pour valider les règles avant la sauvegarde."""
        self.validate_criteria_rules()
        self.name=self.readable_title()
        super().save(*args, **kwargs)

    def check_user_access(self, user):
        """
        Vérifie si un utilisateur satisfait ce critère d'accès.
        
        Cette méthode implémente la logique de vérification des critères d'accès
        en fonction du type de critère. Pour les tickets d'événement, elle vérifie
        si l'utilisateur a acheté au moins un des tickets requis via une commande
        validée.
        
        Args:
            user: L'utilisateur à vérifier
            
        Returns:
            bool: True si l'utilisateur satisfait le critère, False sinon
        """
        if not self.is_active:
            return False
            
        if not self.criteria_rules:
            return False
            
        try:
            if self.criteria_type == AccessCriteriaTypeEnum.ROLE.value:
                required_roles = self.criteria_rules.get('required_roles', [])
                if not required_roles:
                    return False
                    
                # Optimisation : utilise exists() au lieu de filter().count()
                # Vérifie les rôles à travers l'adhésion à l'organisation
                organization = self.chat_room.event.organization
                membership = user.memberships.filter(organization=organization).first()
                
                if not membership:
                    return False
                    
                return membership.roles.filter(name__in=required_roles).exists()
                
            elif self.criteria_type == AccessCriteriaTypeEnum.EVENT_TICKET.value:
                required_tickets = self.criteria_rules.get('required_tickets', [])
                if not required_tickets:
                    return False
                    
                # Convertit les IDs en UUID et vérifie l'accès
                ticket_ids = []
                
                # Convertit les IDs en UUID, en ignorant les invalides
                for tid in required_tickets:
                    if isinstance(tid, UUID):
                        ticket_ids.append(tid)
                    else:
                        try:
                            ticket_ids.append(UUID(str(tid)))
                        except (ValueError, AttributeError, TypeError) as e:
                            logger.debug(f"ID de ticket invalide ignoré: {tid}, erreur: {e}")
                            continue
                
                if not ticket_ids:  # Si aucun ID valide n'a été trouvé
                    logger.warning("Aucun ID de ticket valide trouvé dans la liste")
                    return False
                
                try:
                    # Vérifie l'accès avec une requête optimisée
                    # Une seule requête avec toutes les conditions nécessaires
                    now = timezone.now()
                    
                    # Construction de la requête avec des logs pour le débogage
                    query = ETicket.objects.filter(
                        Q(related_order__user=user) &
                        Q(related_order__status=OrderStatusEnum.FINISHED.value) &
                        Q(ticket__pk__in=ticket_ids) &
                        Q(expiration_date__gt=now)  # Vérifie que le ticket n'est pas expiré
                    ).select_related(
                        'ticket',  # Optimisation : charge le ticket en une seule requête
                        'related_order'  # Optimisation : charge aussi la commande
                    )
                    # Log la requête SQL pour le débogage
                    logger.debug(f"Requête SQL: {query.query}")
                    
                    # Vérifie que l'utilisateur a au moins un ticket valide
                    for e_ticket in query:
                        if e_ticket.related_order.is_valid:
                            logger.info(f"Accès accordé pour l'utilisateur {user.pk} avec le ticket {e_ticket.pk}")
                            return True
                    
                    logger.info(f"Accès refusé pour l'utilisateur {user.pk} - aucun ticket valide")
                    return False
                except Exception as e:
                    # Log l'erreur et retourne False pour éviter les fuites d'information
                    logger.error(f"Erreur lors de la vérification des tickets: {str(e)}")
                    return False
                    
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des critères d'accès: {str(e)}")
            return False  # Par défaut, refuse l'accès en cas d'erreur
        return False  # Par défaut, refuse l'accès
