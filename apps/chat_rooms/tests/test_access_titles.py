# -*- coding: utf-8 -*-
"""
Tests pour le service de génération de titres des critères d'accès.
"""

from django.test import TestCase
from django.core.cache import cache
from django.utils.translation import gettext as _

from apps.chat_rooms.models import ChatRoom, ChatRoomAccessCriteria
from apps.chat_rooms.services.access_title_service import AccessTitleService
from apps.xlib.enums import AccessCriteriaTypeEnum, ChatRoomVisibilityEnum
from apps.events.models import Event, Ticket

class AccessTitleServiceTest(TestCase):
    """Tests du service de génération de titres pour les critères d'accès."""
    
    def setUp(self):
        """Initialise les données de test."""
        # Création d'un événement
        self.event = Event.objects.create(
            name="Test Event",
            description="Test Description",
            type=self.event_type,
            default_price=Decimal('10.00'),
            location_name="Test Venue",
            location_lat=6.3702928,
            location_long=2.3912362,
            date=datetime.date.today() + datetime.timedelta(days=30),
            hour=datetime.time(18, 0),  # 18h00
            expiry_date=datetime.datetime.now() + datetime.timedelta(days=31),
            cover_image=self.test_image,
            publisher=self.user,
            organization=self.organization,
            valid=True,
            have_passed_validation=True
        )
        
        # Création d'un salon
        self.chat_room = ChatRoom.objects.create(
            title="Test Room",
            visibility=ChatRoomVisibilityEnum.PRIVATE.value,
            event=self.event
        )
        
        # Création de tickets
        self.ticket1 = Ticket.objects.create(
            name="VIP Pass",
            event=self.event
        )
        self.ticket2 = Ticket.objects.create(
            name="Regular Pass",
            event=self.event
        )
        
        
        # Nettoyage du cache
        cache.clear()
    
    def test_generate_role_title(self):
        """Teste la génération de titre pour les critères basés sur les rôles."""
        criteria = ChatRoomAccessCriteria.objects.create(
            chat_room=self.chat_room,
            name="Role Test",
            criteria_type=AccessCriteriaTypeEnum.ROLE.value,
            criteria_rules={"required_roles": ["admin", "moderator"]}
        )
        
        title = AccessTitleService.generate_title(criteria)
        expected = _("Réservé aux utilisateurs avec le(s) rôle(s) : admin, moderator")
        self.assertEqual(title, expected)
    
    def test_generate_ticket_title(self):
        """Teste la génération de titre pour les critères basés sur les tickets."""
        criteria = ChatRoomAccessCriteria.objects.create(
            chat_room=self.chat_room,
            name="Ticket Test",
            criteria_type=AccessCriteriaTypeEnum.EVENT_TICKET.value,
            criteria_rules={"required_tickets": [str(self.ticket1.pk), str(self.ticket2.pk)]}
        )
        
        title = AccessTitleService.generate_title(criteria)
        expected = _("Réservé aux détenteurs des billets : VIP Pass, Regular Pass")
        self.assertEqual(title, expected)
    
    def test_invalid_criteria_type(self):
        """Teste la gestion des types de critères invalides."""
        criteria = ChatRoomAccessCriteria.objects.create(
            chat_room=self.chat_room,
            name="Invalid Test",
            criteria_type="invalid_type",
            criteria_rules={}
        )
        
        title = AccessTitleService.generate_title(criteria)
        expected = _("Réservé aux utilisateurs autorisés")
        self.assertEqual(title, expected)
    
    def test_empty_rules(self):
        """Teste la gestion des règles vides."""
        criteria = ChatRoomAccessCriteria.objects.create(
            chat_room=self.chat_room,
            name="Empty Rules Test",
            criteria_type=AccessCriteriaTypeEnum.ROLE.value,
            criteria_rules={"required_roles": []}
        )
        
        title = AccessTitleService.generate_title(criteria)
        expected = _("Réservé aux utilisateurs autorisés")
        self.assertEqual(title, expected)
    
    def test_caching(self):
        """Teste la mise en cache des titres."""
        criteria = ChatRoomAccessCriteria.objects.create(
            chat_room=self.chat_room,
            name="Cache Test",
            criteria_type=AccessCriteriaTypeEnum.ROLE.value,
            criteria_rules={"required_roles": ["admin"]}
        )
        
        # Premier appel - génère et met en cache
        title1 = AccessTitleService.generate_title(criteria)
        
        # Modification des règles sans sauvegarder
        criteria.criteria_rules = {"required_roles": ["moderator"]}
        
        # Deuxième appel - devrait retourner la version en cache
        title2 = AccessTitleService.generate_title(criteria)
        
        self.assertEqual(title1, title2)
        
        # Nettoyage du cache et régénération
        cache.delete(f"{AccessTitleService.CACHE_KEY_PREFIX}{criteria.pk}")
        title3 = AccessTitleService.generate_title(criteria)
        
        self.assertNotEqual(title2, title3)
    
    def test_error_handling(self):
        """Teste la gestion des erreurs."""
        criteria = ChatRoomAccessCriteria.objects.create(
            chat_room=self.chat_room,
            name="Error Test",
            criteria_type=AccessCriteriaTypeEnum.TICKET.value,
            criteria_rules={"ticket_ids": ["invalid-uuid"]}
        )
        
        title = AccessTitleService.generate_title(criteria)
        expected = _("Réservé aux détenteurs de billets")
        self.assertEqual(title, expected)
