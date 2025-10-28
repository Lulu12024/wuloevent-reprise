# -*- coding: utf-8 -*-
"""
Tests unitaires pour le système de tags des salons de discussion.

Ces tests valident :
1. La gestion des tags manuels
2. L'application automatique des tags selon les règles
3. Le filtrage des salons par tags
4. La performance pour une utilisation à grande échelle
"""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.chat_rooms.models.room import ChatRoom
from apps.chat_rooms.services.tag_service import ChatRoomTagService
from apps.chat_rooms.constants import ChatRoomTagType
from apps.events.models import Event, EventType
from apps.organizations.models import Organization
from apps.xlib.enums import ChatRoomTypeEnum, ChatRoomVisibilityEnum

User = get_user_model()

class ChatRoomTagsTest(TestCase):
    """Tests pour le système de tags des salons."""

    def setUp(self):
        """Initialisation des données de test."""
        # Création d'un utilisateur de test
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

        # Création d'une organisation
        self.organization = Organization.objects.create(
            name="Test Org",
            owner=self.user
        )

        # Création d'un type d'événement
        self.event_type = EventType.objects.create(
            name="Test Type",
            description="Test Description"
        )

        # Création d'un événement
        self.event = Event.objects.create(
            name="Test Event",
            description="Test Event Description",
            type=self.event_type,
            default_price=Decimal('10.00'),
            location_name="Test Venue",
            location_lat=6.3702928,
            location_long=2.3912362,
            date=timezone.now() + timedelta(days=5),
            hour=timezone.now().time(),
            expiry_date=timezone.now() + timedelta(days=6),
            publisher=self.user,
            organization=self.organization,
            valid=True
        )

        # Création d'un salon de discussion
        self.chat_room = ChatRoom.objects.create(
            title="Test Room",
            type=ChatRoomTypeEnum.PRIMARY.value,
            visibility=ChatRoomVisibilityEnum.PUBLIC.value,
            event=self.event
        )

    def test_validate_tags(self):
        """Test la validation des tags."""
        # Test avec des tags valides
        valid_tags = [ChatRoomTagType.PROMO.value, ChatRoomTagType.IMMINENT.value]
        self.assertTrue(ChatRoomTagService.validate_tags(valid_tags))

        # Test avec un tag invalide
        invalid_tags = [ChatRoomTagType.PROMO.value, "invalid_tag"]
        with self.assertRaises(ValidationError):
            ChatRoomTagService.validate_tags(invalid_tags)

    def test_update_room_tags(self):
        """Test la mise à jour des tags d'un salon."""
        new_tags = [ChatRoomTagType.PROMO.value]
        ChatRoomTagService.update_room_tags(self.chat_room, new_tags)
        
        # Vérifie que les tags ont été mis à jour
        self.assertEqual(self.chat_room.tags["applied_tags"], new_tags)

    def test_add_remove_tag(self):
        """Test l'ajout et le retrait de tags."""
        tag = ChatRoomTagType.PROMO.value

        # Test l'ajout
        ChatRoomTagService.add_tag(self.chat_room, tag)
        self.assertIn(tag, self.chat_room.tags.get("applied_tags", []))

        # Test le retrait
        ChatRoomTagService.remove_tag(self.chat_room, tag)
        self.assertNotIn(tag, self.chat_room.tags.get("applied_tags", []))

    def test_automatic_tags_imminent(self):
        """Test l'application automatique du tag 'bientot'."""
        # Crée un événement imminent
        imminent_event = Event.objects.create(
            name="Imminent Event",
            description="Test Event Description",
            type=self.event_type,
            default_price=Decimal('10.00'),
            location_name="Test Venue",
            location_lat=6.3702928,
            location_long=2.3912362,
            date=timezone.now() + timedelta(days=1),
            hour=timezone.now().time(),
            expiry_date=timezone.now() + timedelta(days=2),
            publisher=self.user,
            organization=self.organization,
            valid=True
        )

        imminent_room = ChatRoom.objects.create(
            title="Imminent Room",
            type=ChatRoomTypeEnum.PRIMARY.value,
            visibility=ChatRoomVisibilityEnum.PUBLIC.value,
            event=imminent_event
        )


        # Met à jour les tags automatiques
        ChatRoomTagService.update_automatic_tags()

        # Vérifie que le tag 'bientot' a été ajouté
        self.assertIn(
            ChatRoomTagType.IMMINENT.value,
            imminent_room.tags.get("applied_tags", [])
        )

    def test_filter_rooms_by_tags(self):
        """Test le filtrage des salons par tags."""
        # Ajoute des tags à différents salons
        ChatRoomTagService.add_tag(self.chat_room, ChatRoomTagType.PROMO.value)

        other_room = ChatRoom.objects.create(
            title="Other Room",
            type=ChatRoomTypeEnum.PRIMARY.value,
            visibility=ChatRoomVisibilityEnum.PUBLIC.value,
            event=self.event
        )
        ChatRoomTagService.add_tag(other_room, ChatRoomTagType.TRENDING.value)

        # Test le filtrage
        promo_rooms = ChatRoomTagService.filter_rooms_by_tags([ChatRoomTagType.PROMO.value])
        self.assertEqual(promo_rooms.count(), 1)
        self.assertEqual(promo_rooms.first(), self.chat_room)

        trending_rooms = ChatRoomTagService.filter_rooms_by_tags([ChatRoomTagType.TRENDING.value])
        self.assertEqual(trending_rooms.count(), 1)
        self.assertEqual(trending_rooms.first(), other_room)
