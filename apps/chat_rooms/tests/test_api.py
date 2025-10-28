# -*- coding: utf-8 -*-
"""
Tests d'intégration pour l'API REST des salons de discussion.
Optimisé pour une application à grande échelle avec des millions d'utilisateurs.
"""

import json
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.chat_rooms.models import ChatRoom, ChatRoomAccessCriteria
from apps.events.models import Event, Ticket
from apps.users.models import User 
from apps.xlib.enums import (
    ChatRoomTypeEnum, ChatRoomVisibilityEnum,
    ChatRoomStatusEnum, AccessCriteriaTypeEnum
)

class ChatRoomAPITest(APITestCase):
    """Tests d'intégration pour l'API des salons de discussion."""
    
    def setUp(self):
        """Initialise les données de test."""
        # Création des utilisateurs
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User"
        )
        self.staff_user = User.objects.create_user(
            email="staff@example.com",
            password="staffpass123",
            is_staff=True
        )
        
        # Création de l'organisation
        self.organization = Organization.objects.create(
            name="Test Org",
            description="Test Description"
        )
        
        # Image de test
        self.test_image = SimpleUploadedFile(
            "test.jpg",
            b"file_content",
            content_type="image/jpeg"
        )
        
        # Création de l'événement
        self.event = Event.objects.create(
            name="Test Event",
            description="Test Description",
            type=EventTypeEnum.CONCERT.value,
            default_price=Decimal('10.00'),
            location_name="Test Venue",
            location_lat=6.3702928,
            location_long=2.3912362,
            date=timezone.now().date() + timedelta(days=30),
            hour=datetime.strptime("18:00", "%H:%M").time(),
            expiry_date=timezone.now() + timedelta(days=31),
            cover_image=self.test_image,
            publisher=self.user,
            organization=self.organization,
            valid=True,
            have_passed_validation=True
        )
        
        # Création des tickets
        self.ticket = Ticket.objects.create(
            name="VIP Pass",
            event=self.event,
            price=Decimal('50.00'),
            quantity=100
        )
        
        # Données de base pour un salon
        self.chat_room_data = {
            'title': 'Test Chat Room',
            'type': ChatRoomTypeEnum.PRIMARY.value,
            'visibility': ChatRoomVisibilityEnum.PUBLIC.value,
            'status': ChatRoomStatusEnum.ACTIVE.value,
            'event_id': str(self.event.id)
        }
        
        # URLs
        self.list_url = reverse('chatroom-list')
        
        # Authentification
        self.client.force_authenticate(user=self.user)
    
    def test_create_chat_room(self):
        """Teste la création d'un salon."""
        response = self.client.post(
            self.list_url,
            self.chat_room_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ChatRoom.objects.count(), 1)
        self.assertEqual(
            ChatRoom.objects.get().title,
            self.chat_room_data['title']
        )
    
    def test_list_chat_rooms(self):
        """Teste la liste des salons avec pagination."""
        # Crée 15 salons
        for i in range(15):
            ChatRoom.objects.create(
                title=f"Room {i}",
                type=ChatRoomTypeEnum.PRIMARY.value,
                visibility=ChatRoomVisibilityEnum.PUBLIC.value,
                status=ChatRoomStatusEnum.ACTIVE.value,
                event=self.event
            )
        
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)  # Page size
        self.assertIsNotNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
    
    def test_retrieve_chat_room(self):
        """Teste la récupération d'un salon spécifique."""
        room = ChatRoom.objects.create(**{
            'title': 'Test Room',
            'type': ChatRoomTypeEnum.PRIMARY.value,
            'visibility': ChatRoomVisibilityEnum.PUBLIC.value,
            'status': ChatRoomStatusEnum.ACTIVE.value,
            'event': self.event
        })
        
        url = reverse('chatroom-detail', args=[room.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], room.title)
    
    def test_update_chat_room(self):
        """Teste la mise à jour d'un salon."""
        room = ChatRoom.objects.create(**{
            'title': 'Old Title',
            'type': ChatRoomTypeEnum.PRIMARY.value,
            'visibility': ChatRoomVisibilityEnum.PUBLIC.value,
            'status': ChatRoomStatusEnum.ACTIVE.value,
            'event': self.event
        })
        
        url = reverse('chatroom-detail', args=[room.id])
        data = {'title': 'New Title'}
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            ChatRoom.objects.get(id=room.id).title,
            'New Title'
        )
    
    def test_delete_chat_room(self):
        """Teste la suppression d'un salon."""
        room = ChatRoom.objects.create(**{
            'title': 'Test Room',
            'type': ChatRoomTypeEnum.PRIMARY.value,
            'visibility': ChatRoomVisibilityEnum.PUBLIC.value,
            'status': ChatRoomStatusEnum.ACTIVE.value,
            'event': self.event
        })
        
        url = reverse('chatroom-detail', args=[room.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ChatRoom.objects.count(), 0)
    
    def test_filter_by_event(self):
        """Teste le filtrage des salons par événement."""
        # Crée des salons pour différents événements
        other_event = Event.objects.create(
            name="Other Event",
            description="Other Description",
            type=EventTypeEnum.CONCERT.value,
            default_price=Decimal('10.00'),
            location_name="Other Venue",
            location_lat=6.3702928,
            location_long=2.3912362,
            date=timezone.now().date() + timedelta(days=30),
            hour=datetime.strptime("18:00", "%H:%M").time(),
            expiry_date=timezone.now() + timedelta(days=31),
            cover_image=self.test_image,
            publisher=self.user,
            organization=self.organization,
            valid=True,
            have_passed_validation=True
        )
        
        ChatRoom.objects.create(**{
            'title': 'Room 1',
            'type': ChatRoomTypeEnum.PRIMARY.value,
            'visibility': ChatRoomVisibilityEnum.PUBLIC.value,
            'status': ChatRoomStatusEnum.ACTIVE.value,
            'event': self.event
        })
        ChatRoom.objects.create(**{
            'title': 'Room 2',
            'type': ChatRoomTypeEnum.PRIMARY.value,
            'visibility': ChatRoomVisibilityEnum.PUBLIC.value,
            'status': ChatRoomStatusEnum.ACTIVE.value,
            'event': other_event
        })
        
        url = reverse('chatroom-by-event')
        response = self.client.get(
            url,
            {'event_id': str(self.event.id)}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(
            response.data['results'][0]['title'],
            'Room 1'
        )
    
    def test_add_access_criteria(self):
        """Teste l'ajout de critères d'accès à un salon."""
        room = ChatRoom.objects.create(**{
            'title': 'Private Room',
            'type': ChatRoomTypeEnum.PRIMARY.value,
            'visibility': ChatRoomVisibilityEnum.PRIVATE.value,
            'status': ChatRoomStatusEnum.ACTIVE.value,
            'event': self.event
        })
        
        url = reverse('chatroom-add-access-criteria', args=[room.id])
        data = {
            'name': 'VIP Access',
            'criteria_type': AccessCriteriaTypeEnum.EVENT_TICKET.value,
            'criteria_rules': {
                'required_tickets': [str(self.ticket.id)]
            }
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            ChatRoomAccessCriteria.objects.filter(chat_room=room).count(),
            1
        )
    
    def test_search_chat_rooms(self):
        """Teste la recherche de salons."""
        ChatRoom.objects.create(**{
            'title': 'Concert VIP Room',
            'type': ChatRoomTypeEnum.PRIMARY.value,
            'visibility': ChatRoomVisibilityEnum.PUBLIC.value,
            'status': ChatRoomStatusEnum.ACTIVE.value,
            'event': self.event
        })
        ChatRoom.objects.create(**{
            'title': 'Regular Room',
            'type': ChatRoomTypeEnum.SECONDARY.value,
            'visibility': ChatRoomVisibilityEnum.PUBLIC.value,
            'status': ChatRoomStatusEnum.ACTIVE.value,
            'event': self.event
        })
        
        response = self.client.get(
            self.list_url,
            {'search': 'VIP'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(
            response.data['results'][0]['title'],
            'Concert VIP Room'
        )
    
    def test_unauthorized_access(self):
        """Teste l'accès non autorisé."""
        self.client.force_authenticate(user=None)
        
        response = self.client.get(self.list_url)
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )
    
    def test_staff_access(self):
        """Teste l'accès staff."""
        self.client.force_authenticate(user=self.staff_user)
        
        # Crée un salon privé
        ChatRoom.objects.create(**{
            'title': 'Staff Only Room',
            'type': ChatRoomTypeEnum.PRIMARY.value,
            'visibility': ChatRoomVisibilityEnum.PRIVATE.value,
            'status': ChatRoomStatusEnum.ACTIVE.value,
            'event': self.event
        })
        
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
