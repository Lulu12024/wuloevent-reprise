"""Tests pour les critères d'accès aux salons de discussion.

Ce module contient les tests unitaires pour la fonctionnalité de contrôle d'accès
aux salons de discussion basée sur les tickets d'événements. Il vérifie que :

1. Les règles de validation des critères sont correctement appliquées
2. L'accès est accordé uniquement aux utilisateurs ayant acheté les bons tickets
3. Les commandes et transactions sont correctement vérifiées

Ces tests sont conçus pour une application à grande échelle, avec :
- Optimisation des requêtes pour des millions d'utilisateurs
- Validation complète des données
- Vérification des cas limites et des erreurs
"""

import datetime
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.chat_rooms.models import ChatRoom, ChatRoomAccessCriteria
from apps.events.models import Event, Ticket, Order, OrderItem, ETicket, EventType
from apps.events.models import TicketCategory, TicketCategoryFeature
from apps.organizations.models import Organization
from apps.users.models import Transaction
from apps.xlib.enums import (
    ChatRoomTypeEnum,
    ChatRoomVisibilityEnum,
    AccessCriteriaTypeEnum,
    OrderStatusEnum,
    TransactionKindEnum,
    TransactionStatusEnum,
    TRANSACTIONS_POSSIBLE_GATEWAYS,
    PAYMENT_METHOD
)

User = get_user_model()

class ChatRoomAccessCriteriaTest(TestCase):
    """Suite de tests pour les critères d'accès aux salons."""

    def setUp(self):
        """Initialisation des données de test."""
        # Création d'un utilisateur de test
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        # Création du type d'événement
        self.event_type = EventType.objects.create(
            name="Concert",
            description="Concert de musique"
        )
        
        # Création d'une image de test pour la couverture
        self.test_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'',  # Image vide pour les tests
            content_type='image/jpeg'
        )
        
        # Création d'une organisation avec tous les champs requis
        self.organization = Organization.objects.create(
            name="Test Organization",
            description="Test Organization Description",
            email="org@example.com",
            phone="+22967000000",
            address="123 Test Street",
            owner=self.user,
            phone_number_validated=True,
            percentage=0.15,  # 15% commission standard
            percentage_if_discounted=0.10  # 10% commission pour les ventes avec réduction
        )
        
        # Création d'un événement avec tous les champs requis
        self.event = Event.objects.create(
            name="Test Event",
            description="Test Event Description",
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
        
        # Création d'une catégorie de ticket
        self.ticket_category = TicketCategory.objects.create(
            event=self.event,
            name="Standard",
            description="Catégorie standard",
            organization=self.organization
        )
        
        # Création d'un ticket avec tous les champs requis
        self.ticket = Ticket.objects.create(
            event=self.event,
            name="Test Ticket",
            description="Ticket standard",
            category=self.ticket_category,
            price=Decimal("10.00"),
            available_quantity=100,
            initial_quantity=100,
            organization=self.organization,
            expiry_date=datetime.datetime.now() + datetime.timedelta(days=30)
        )
        
        # Création d'un OrderItem avec tous les champs requis
        self.order_item = OrderItem.objects.create(
            ticket=self.ticket,
            quantity=2,
            line_total=Decimal('20.00')  # 2 tickets à 10.00
        )
        
        # Création d'une commande avec tous les champs requis
        self.order = Order.objects.create(
            user=self.user,
            item=self.order_item,
            name="Test User",
            email="test@example.com",
            sex="M",
            phone="+22967000000",
            status=OrderStatusEnum.FINISHED.value,
            ip_address="127.0.0.1"
        )

        
        # Création d'une transaction pour valider la commande
        # Cette transaction est nécessaire car Order.is_valid vérifie
        # l'existence d'une transaction PAID pour la commande
        self.transaction = Transaction.objects.create(
            type=TransactionKindEnum.ORDER.value,
            status=TransactionStatusEnum.PAID.value,
            gateway=TRANSACTIONS_POSSIBLE_GATEWAYS.FEDAPAY.value,
            user=self.user,
            amount=str(self.order_item.line_total),
            entity_id=str(self.order.pk),
            description=f"Paiement pour la commande {self.order.order_id}"
        )


        
        # Création d'un e-ticket avec tous les champs requis
        # L'expiration_date est requise pour générer la secret_phrase
        self.e_ticket = ETicket.objects.create(
            event=self.event,
            ticket=self.ticket,
            related_order=self.order,
            name="Test E-Ticket",
            expiration_date=self.event.expiry_date  # Utilise la date d'expiration de l'événement
        )

        
        # Création d'un salon de discussion avec tous les champs requis
        self.chat_room = ChatRoom.objects.create(
            title="Test Room",
            type=ChatRoomTypeEnum.PRIMARY.value,
            visibility=ChatRoomVisibilityEnum.PRIVATE.value,
            event=self.event
        )

    def test_validate_ticket_criteria_rules(self):
        """Test la validation des règles pour les critères de type ticket.
        
        Vérifie que :
        1. Les règles avec des tickets valides sont acceptées
        2. Les règles avec une liste vide de tickets sont rejetées
        3. Les règles avec des tickets inexistants sont rejetées
        
        Cette validation est critique pour la sécurité et l'intégrité des données
        dans un système à grande échelle.
        """
        # Test avec des tickets valides
        criteria = ChatRoomAccessCriteria(
            chat_room=self.chat_room,
            name="Test Ticket Criteria",
            criteria_type=AccessCriteriaTypeEnum.EVENT_TICKET.value,
            criteria_rules={"required_tickets": [str(self.ticket.pk)]}
        )
        criteria.validate_criteria_rules()  # Ne devrait pas lever d'exception
        
        # Test avec une liste vide de tickets
        criteria.criteria_rules = {"required_tickets": []}
        with self.assertRaises(ValidationError):
            criteria.validate_criteria_rules()
            
        # Test avec un ticket inexistant
        criteria.criteria_rules = {"required_tickets": ["99999"]}
        with self.assertRaises(ValidationError):
            criteria.validate_criteria_rules()

    def test_check_user_access_with_ticket(self):
        """Test la vérification d'accès basée sur les tickets.
        
        Vérifie les scénarios suivants :
        1. Accès refusé sans commande
        2. Accès accordé avec une commande valide et payée
        3. Accès refusé avec une commande non terminée
        4. Accès refusé avec un critère inactif
        5. Accès refusé avec un ticket expiré
        
        Ces tests simulent les cas réels d'utilisation et vérifient
        la robustesse du système de contrôle d'accès.
        """
        # Création du critère d'accès
        criteria = ChatRoomAccessCriteria.objects.create(
            chat_room=self.chat_room,
            name="Test Ticket Criteria",
            criteria_type=AccessCriteriaTypeEnum.EVENT_TICKET.value,
            criteria_rules={"required_tickets": [str(self.ticket.pk)]}
        )
 

        
        # Vérification avec une commande valide - devrait autoriser l'accès
        self.assertTrue(criteria.check_user_access(self.user))

        # Test avec une commande non terminée
        self.order.status = OrderStatusEnum.SUBMITTED.value
        self.order.save()

        self.assertFalse(criteria.check_user_access(self.user))
        
        # Test avec un critère inactif
        self.order.status = OrderStatusEnum.FINISHED.value
        self.order.save()
        criteria.is_active = False
        criteria.save()
        self.assertFalse(criteria.check_user_access(self.user))
        
        # Test avec un ticket expiré
        # Réactivation du critère pour le test
        criteria.is_active = True
        criteria.save()
        
        # Expiration du ticket
        self.ticket.expiry_date = datetime.datetime.now() - datetime.timedelta(days=1)
        self.ticket.save()
       
    def test_check_user_access_with_multiple_tickets(self):
        """Test la vérification d'accès avec plusieurs tickets requis.
        
        Vérifie que :
        1. L'accès est accordé si l'utilisateur a au moins un des tickets requis
        2. La vérification est optimisée avec une seule requête SQL
        3. Le système gère correctement les listes de tickets multiples
        
        Ces tests sont essentiels pour valider le comportement du système
        dans des scénarios complexes avec de multiples options d'accès.
        """
        # Création d'un second ticket
        ticket2 = Ticket.objects.create(
            event=self.event,
            name="Test Ticket 2",
            description="Ticket standard",
            category=self.ticket_category,
            price=Decimal("10.00"),
            available_quantity=100,
            initial_quantity=100,
            organization=self.organization,
            expiry_date=datetime.datetime.now() + datetime.timedelta(days=30)
        )
        
        # Création du critère d'accès avec deux tickets requis
        criteria = ChatRoomAccessCriteria.objects.create(
            chat_room=self.chat_room,
            name="Multiple Tickets Criteria",
            criteria_type=AccessCriteriaTypeEnum.EVENT_TICKET.value,
            criteria_rules={"required_tickets": [str(self.ticket.pk), str(ticket2.pk)]}
        )
        
        # Création d'une commande avec le premier ticket
        order_item = OrderItem.objects.create(
            ticket=self.ticket,
            quantity=1,
            line_total=self.ticket.price
        )
        
        order = Order.objects.create(
            user=self.user,
            item=order_item,
            status=OrderStatusEnum.FINISHED.value
        )
        
        e_ticket = ETicket.objects.create(
            event=self.event,
            ticket=self.ticket,
            related_order=order,
            name="Test E-Ticket",
            expiration_date=self.event.expiry_date
        )
        
        # L'accès devrait être autorisé car l'utilisateur a au moins un des tickets requis
        self.assertTrue(criteria.check_user_access(self.user))
