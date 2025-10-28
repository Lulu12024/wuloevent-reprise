# -*- coding: utf-8 -*-
"""
Tests pour la pagination et les permissions de l'API des salons de discussion.
Optimisé pour une application à grande échelle avec des millions d'utilisateurs.
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.utils.timezone import now
from decimal import Decimal
from datetime import timedelta

from apps.chat_rooms.models import ChatRoom
from apps.chat_rooms.paginator import ChatRoomPagination
from apps.events.models import Event
from apps.users.models import User
from apps.organizations.models import Organization
from apps.xlib.enums import ChatRoomVisibilityEnum, ChatRoomTypeEnum, ChatRoomStatusEnum

class ChatRoomAPITestCase(APITestCase):
    """Tests pour l'API des salons avec focus sur la pagination et les permissions."""

    @classmethod
    def setUpTestData(cls):
        """Initialise les données de test partagées."""
        # Création des utilisateurs
        cls.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123"
        )
        cls.regular_user = User.objects.create_user(
            email="user@example.com",
            password="userpass123"
        )
        cls.event_manager = User.objects.create_user(
            email="manager@example.com",
            password="managerpass123"
        )

        # Création de l'organisation
        cls.organization = Organization.objects.create(
            name="Test Organization",
            description="Test Description"
        )

        # Création de l'événement
        cls.event = Event.objects.create(
            name="Test Event",
            description="Test Description",
            type="concert",
            default_price=Decimal('10.00'),
            location_name="Test Venue",
            location_lat=6.3702928,
            location_long=2.3912362,
            date=now().date() + timedelta(days=30),
            expiry_date=now() + timedelta(days=31),
            publisher=cls.event_manager,
            organization=cls.organization,
            valid=True,
            have_passed_validation=True
        )

    def setUp(self):
        """Initialise l'environnement de test."""
        self.list_url = reverse('chatroom-list')
        self.by_event_url = reverse('chatroom-by-event')

        # Création de salons de test
        self.rooms = []
        for i in range(25):  # Crée plus que la taille de page par défaut
            room = ChatRoom.objects.create(
                title=f"Room {i}",
                type=ChatRoomTypeEnum.PRIMARY.value,
                visibility=ChatRoomVisibilityEnum.PUBLIC.value,
                status=ChatRoomStatusEnum.ACTIVE.value,
                event=self.event
            )
            self.rooms.append(room)

    def test_pagination_default_size(self):
        """Teste la pagination avec la taille par défaut."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), ChatRoomPagination.page_size)
        self.assertIsNotNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(response.data['current_page'], 1)

    def test_pagination_custom_size(self):
        """Teste la pagination avec une taille personnalisée."""
        custom_size = 10
        response = self.client.get(f"{self.list_url}?page_size={custom_size}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), custom_size)

    def test_pagination_max_size_limit(self):
        """Teste la limite maximale de la taille de page."""
        over_max_size = ChatRoomPagination.max_page_size + 10
        response = self.client.get(f"{self.list_url}?page_size={over_max_size}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data['results']),
            ChatRoomPagination.max_page_size
        )

    def test_pagination_metadata(self):
        """Teste les métadonnées de pagination."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('current_page', response.data)
        self.assertIn('total_pages', response.data)
        self.assertEqual(response.data['count'], len(self.rooms))

    def test_admin_access_all_rooms(self):
        """Teste l'accès administrateur à tous les salons."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], len(self.rooms))

    def test_public_access_public_rooms(self):
        """Teste l'accès public aux salons publics."""
        # Crée un mélange de salons publics et privés
        ChatRoom.objects.all().delete()
        public_rooms = []
        private_rooms = []
        
        for i in range(5):
            public_room = ChatRoom.objects.create(
                title=f"Public Room {i}",
                type=ChatRoomTypeEnum.PRIMARY.value,
                visibility=ChatRoomVisibilityEnum.PUBLIC.value,
                status=ChatRoomStatusEnum.ACTIVE.value,
                event=self.event
            )
            public_rooms.append(public_room)
            
            private_room = ChatRoom.objects.create(
                title=f"Private Room {i}",
                type=ChatRoomTypeEnum.PRIMARY.value,
                visibility=ChatRoomVisibilityEnum.PRIVATE.value,
                status=ChatRoomStatusEnum.ACTIVE.value,
                event=self.event
            )
            private_rooms.append(private_room)

        # Test sans authentification
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], len(public_rooms))

    def test_event_manager_access(self):
        """Teste l'accès du gestionnaire d'événement."""
        self.client.force_authenticate(user=self.event_manager)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Le gestionnaire devrait voir tous les salons de son événement
        event_rooms = ChatRoom.objects.filter(event=self.event).count()
        self.assertEqual(response.data['count'], event_rooms)

    def test_invalid_page(self):
        """Teste la gestion des numéros de page invalides."""
        invalid_page = 999
        response = self.client.get(f"{self.list_url}?p={invalid_page}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_by_event_pagination(self):
        """Teste la pagination pour le filtrage par événement."""
        response = self.client.get(
            f"{self.by_event_url}?event_id={self.event.id}&page_size=10"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
        self.assertIsNotNone(response.data['next'])
        self.assertEqual(response.data['count'], len(self.rooms))
