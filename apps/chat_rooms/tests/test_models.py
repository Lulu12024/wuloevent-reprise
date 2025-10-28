import json
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.events.models import Event
from apps.chat_rooms.models import (
    ChatRoom,
    ChatRoomSubscription,
    ChatRoomPreference,
    ChatRoomAccessCriteria
)

User = get_user_model()

class ChatRoomModelTest(TestCase):
    """Suite de tests pour le modèle ChatRoom.
    
    Cette suite teste toutes les fonctionnalités du modèle ChatRoom,
    y compris la création, les contraintes, et les règles d'accès.
    """

    """Test suite for the ChatRoom model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.event = Event.objects.create(
            title='Test Event',
            creator=self.user
        )
        self.chat_room = ChatRoom.objects.create(
            title='Test Room',
            type=ChatRoomTypeEnum.PRIMARY.value,
            visibility=ChatRoomVisibilityEnum.PUBLIC.value,
            event=self.event,
            tags={'category': 'test'}
        )
        
        # Créer des critères d'accès pour les tests
        self.access_criteria = ChatRoomAccessCriteria.objects.create(
            chat_room=self.chat_room,
            name='Test Criteria',
            criteria_type=AccessCriteriaTypeEnum.ROLE.value,
            criteria_rules={'required_role': 'admin'}
        )

    def test_chat_room_creation(self):
        """Test la création d'un salon avec tous les champs requis."""

        """Test that a chat room can be created with all fields."""
        self.assertEqual(self.chat_room.title, 'Test Room')
        self.assertEqual(self.chat_room.type, ChatRoom.RoomType.PRIMARY)
        self.assertEqual(self.chat_room.visibility, ChatRoom.Visibility.PUBLIC)
        self.assertEqual(self.chat_room.status, ChatRoom.Status.ACTIVE)
        self.assertIsNotNone(self.chat_room.created_at)
        self.assertIsNotNone(self.chat_room.updated_at)

    def test_chat_room_str_representation(self):
        """Test la représentation string du salon."""

        """Test the string representation of ChatRoom."""
        expected_str = f"Test Room (Principal)"
        self.assertEqual(str(self.chat_room), expected_str)

    def test_json_fields(self):
        """Test que les champs JSON stockent et récupèrent correctement les données."""

        """Test that JSON fields store and retrieve data correctly."""
        self.assertEqual(self.chat_room.tags['category'], 'test')
        self.assertTrue(self.chat_room.access_rules['allow_guests'])


class ChatRoomSubscriptionTest(TestCase):
    """Test suite for the ChatRoomSubscription model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.event = Event.objects.create(
            title='Test Event',
            creator=self.user
        )
        self.chat_room = ChatRoom.objects.create(
            title='Test Room',
            event=self.event
        )
        self.subscription = ChatRoomSubscription.objects.create(
            user=self.user,
            chat_room=self.chat_room,
            is_admin=True
        )

    def test_subscription_creation(self):
        """Test la création d'un abonnement avec tous les champs requis."""

        """Test that a subscription can be created with all fields."""
        self.assertEqual(self.subscription.user, self.user)
        self.assertEqual(self.subscription.chat_room, self.chat_room)
        self.assertTrue(self.subscription.is_admin)
        self.assertIsNotNone(self.subscription.joined_at)

    def test_unique_constraint(self):
        """Test that a user cannot subscribe to the same room twice."""
        with self.assertRaises(ValidationError):
            ChatRoomSubscription.objects.create(
                user=self.user,
                chat_room=self.chat_room
            )


class ChatRoomPreferenceTest(TestCase):
    """Test suite for the ChatRoomPreference model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.event = Event.objects.create(
            title='Test Event',
            creator=self.user
        )
        self.chat_room = ChatRoom.objects.create(
            title='Test Room',
            event=self.event
        )
        self.preference = ChatRoomPreference.objects.create(
            user=self.user,
            chat_room=self.chat_room,
            custom_name='My Test Room',
            is_muted=True,
            notification_level='mentions'
        )

    def test_preference_creation(self):
        """Test la création des préférences avec tous les champs requis."""

        """Test that preferences can be created with all fields."""
        self.assertEqual(self.preference.custom_name, 'My Test Room')
        self.assertTrue(self.preference.is_muted)
        self.assertEqual(self.preference.notification_level, 'mentions')

    def test_unique_constraint(self):
        """Test that a user cannot have multiple preferences for the same room."""
        with self.assertRaises(ValidationError):
            ChatRoomPreference.objects.create(
                user=self.user,
                chat_room=self.chat_room
            )


class ChatRoomAccessCriteriaTest(TestCase):
    """Test suite for the ChatRoomAccessCriteria model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.event = Event.objects.create(
            title='Test Event',
            creator=self.user
        )
        self.chat_room = ChatRoom.objects.create(
            title='Test Room',
            event=self.event,
            visibility=ChatRoom.Visibility.PRIVATE
        )
        self.criteria = ChatRoomAccessCriteria.objects.create(
            chat_room=self.chat_room,
            name='Role Based Access',
            description='Only admins can access',
            criteria_type='role',
            criteria_rules={'required_role': 'admin'}
        )

    def test_criteria_creation(self):
        """Test la création des critères d'accès avec tous les champs requis."""

        """Test that access criteria can be created with all fields."""
        self.assertEqual(self.criteria.name, 'Role Based Access')
        self.assertEqual(self.criteria.criteria_type, 'role')
        self.assertEqual(
            self.criteria.criteria_rules['required_role'],
            'admin'
        )
        self.assertTrue(self.criteria.is_active)

    def test_check_user_access(self):
        """Test la fonctionnalité de vérification d'accès utilisateur."""

        """Test the user access checking functionality."""
        # Basic test - should be implemented based on actual access logic
        self.assertTrue(self.criteria.check_user_access(self.user))

    def test_inactive_criteria(self):
        """Test que les critères inactifs refusent toujours l'accès."""

        """Test that inactive criteria always deny access."""
        self.criteria.is_active = False
        self.criteria.save()
        self.assertFalse(self.criteria.check_user_access(self.user))
