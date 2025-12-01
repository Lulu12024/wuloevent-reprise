# -*- coding: utf-8 -*-
"""
Serializers pour les événements éphémères 
API de création d'événements éphémères par les super-vendeurs


@author:
    Beaudelaire LAHOUME, alias root-lr
"""

import logging
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.events.models import Event, EventType
from apps.organizations.models import Organization
from apps.users.serializers import UserSerializerLight
from apps.events.serializers.types import EventTypeSerializer
from apps.organizations.serializers import OrganizationSerializerLight
from apps.utils.models import Country
from apps.xlib.error_util import ErrorUtil, ErrorEnum

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class EphemeralEventCreationSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création d'événements éphémères par les super-vendeurs.
    
    Fonctionnalités :
    - Validation que le créateur est un super-vendeur vérifié
    - Marquage automatique comme éphémère
    - Génération automatique du code d'accès unique
    - Ne crée pas de chatroom (événements privés)
    
    Endpoint : POST /api/super-sellers/events/ephemeral
    """
    
    type = serializers.PrimaryKeyRelatedField(
        queryset=EventType.objects.filter(active=True),
        required=True
    )
    
    organization = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=Organization.objects.filter(
            organization_type='SUPER_SELLER',
            active=True
        ),
        required=True,
        help_text="Organisation super-vendeur (doit être vérifiée)"
    )
    
    country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(),
        required=False,
        allow_null=True
    )
    
    # Champs calculés/générés automatiquement (read_only)
    is_ephemeral = serializers.BooleanField(read_only=True)
    ephemeral_access_code = serializers.CharField(read_only=True)
    ephemeral_access_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = (
            # Identifiants
            'pk',
            
            # Informations de base
            'name',
            'description',
            'type',
            'organization',
            
            # Détails événement
            'default_price',
            'date',
            'hour',
            'expiry_date',
            'cover_image',
            
            # Localisation
            'location_name',
            'location_lat',
            'location_long',
            'country',
            
            # Limites
            'participant_limit',
            'participant_count',
            
            # Champs éphémères (read_only)
            'is_ephemeral',
            'ephemeral_access_code',
            'ephemeral_access_url',
        )
        
        read_only_fields = (
            'pk',
            'is_ephemeral',
            'ephemeral_access_code',
            'ephemeral_access_url',
            'participant_count',
        )
    
    def get_ephemeral_access_url(self, obj):
        """Retourne l'URL d'accès unique pour l'événement éphémère"""
        return obj.get_ephemeral_access_url() if obj else None
    
    def validate_organization(self, value):
        """
        Valide que l'organisation est un super-vendeur vérifié.
        
        Critères :
        1. Organisation de type SUPER_SELLER
        2. Profil super-vendeur existe
        3. KYC vérifié (status = VERIFIED)
        4. Organisation active
        """
        # Vérifier que c'est bien un super-vendeur
        if value.organization_type != 'SUPER_SELLER':
            raise ValidationError(
                "Seules les organisations de type Super-Vendeur peuvent créer des événements éphémères.",
                code='invalid_organization_type'
            )
        
        # Vérifier que le profil super-vendeur existe
        # if not hasattr(value, 'super_seller_profile'):
        #     raise ValidationError(
        #         "Cette organisation n'a pas de profil Super-Vendeur.",
        #         code='missing_super_seller_profile'
        #     )
        
        # # Vérifier que le KYC est vérifié
        # if not value.super_seller_profile.is_kyc_verified():
        #     raise ValidationError(
        #         "Le KYC du super-vendeur doit être vérifié pour créer des événements éphémères. "
        #         f"Statut actuel : {value.super_seller_profile.get_kyc_status_display()}",
        #         code='kyc_not_verified'
        #     )
        
        # Vérifier que l'organisation est active
        if not value.active:
            raise ValidationError(
                "L'organisation doit être active.",
                code='organization_inactive'
            )
        
        return value
    
    def validate(self, attrs):
        """Validations globales"""
        data = super().validate(attrs)
        
        # Validation date/heure (empêcher événements dans le passé)
        from django.utils import timezone
        import datetime
        
        hour = data.get("hour")
        date = data.get("date")
        
        if not hour:
            hour = datetime.time(0, 0, 0)
            data['hour'] = hour
        
        event_datetime = timezone.make_aware(
            datetime.datetime.combine(date, hour),
            timezone.get_default_timezone()
        )
        
        current_datetime = timezone.now()
        
        if current_datetime >= event_datetime:
            raise ValidationError(
                {
                    'date': "La date de l'événement doit être dans le futur."
                },
                code='past_date'
            )
        
        # Validation participant_limit vs participant_count
        participant_count = attrs.get('participant_count', 0)
        participant_limit = attrs.get('participant_limit')
        
        if participant_limit and participant_count > participant_limit:
            raise ValidationError(
                {
                    'participant_count': "Le nombre de participants ne peut pas dépasser la limite."
                },
                code='participant_count_exceeds_limit'
            )
        
        return data
    
    def create(self, validated_data):
        """
        Crée l'événement éphémère avec configuration automatique.
        
        Actions automatiques :
        1. Marquer is_ephemeral = True
        2. Définir created_by_super_seller
        3. Définir publisher (utilisateur authentifié)
        4. Générer le code d'accès unique
        5. Marquer comme private = True
        6. NE PAS créer de chatroom
        """
        request = self.context.get('request')
        
        # 1. Marquer comme éphémère
        validated_data['is_ephemeral'] = True
        
        # 2. Définir le super-vendeur créateur
        validated_data['created_by_super_seller'] = validated_data['organization']
        
        # 3. Définir le publisher (utilisateur authentifié)
        if request and request.user:
            validated_data['publisher'] = request.user
        
        # 4. Marquer comme privé
        validated_data['private'] = True
        
        # 5. Créer l'événement
        instance = super().create(validated_data)
        instance.save()
        
        # 6. Générer le code d'accès unique
        instance.generate_ephemeral_access_code()
        
        logger.info(
            f"Événement éphémère créé : {instance.name} (Code: {instance.ephemeral_access_code}) "
            f"par {validated_data['organization'].name}"
        )
        
        # Note : Pas de création de chatroom pour les événements éphémères
        
        return instance


class EphemeralEventDetailSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'affichage détaillé d'un événement éphémère.
    
    Utilisé pour :
    - Réponse après création (POST)
    - Détails d'un événement éphémère (GET)
    - Listing des événements éphémères d'un super-vendeur
    """
    
    type = EventTypeSerializer(read_only=True)
    organization = OrganizationSerializerLight(read_only=True)
    created_by_super_seller = OrganizationSerializerLight(read_only=True)
    publisher = UserSerializerLight(read_only=True)
    ephemeral_access_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = (
            # Identifiants
            'pk',
            'uuid',
            
            # Informations de base
            'name',
            'description',
            'type',
            'organization',
            'publisher',
            
            # Détails événement
            'default_price',
            'date',
            'hour',
            'expiry_date',
            'cover_image',
            'views',
            
            # Localisation
            'location_name',
            'location_lat',
            'location_long',
            'country',
            
            # Participants
            'participant_limit',
            'participant_count',
            
            # Validation
            'valid',
            'have_passed_validation',
            
            # Champs éphémères
            'is_ephemeral',
            'created_by_super_seller',
            'ephemeral_access_code',
            'ephemeral_access_url',
            
            # Dates
            'timestamp',
            'updated',
        )
        
        read_only_fields = fields  # Tous les champs en lecture seule
    
    def get_ephemeral_access_url(self, obj):
        """Retourne l'URL d'accès complète"""
        return obj.get_ephemeral_access_url()


class EphemeralEventListSerializer(serializers.ModelSerializer):
    """
    Serializer léger pour le listing des événements éphémères.
    
    Utilisé pour :
    - Liste des événements éphémères d'un super-vendeur
    - Recherche dans les événements éphémères
    """
    
    type = EventTypeSerializer(read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    ephemeral_access_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = (
            'pk',
            'name',
            'description',
            'type',
            'organization_name',
            'default_price',
            'date',
            'hour',
            'location_name',
            'cover_image',
            'participant_count',
            'participant_limit',
            'is_ephemeral',
            'ephemeral_access_code',
            'ephemeral_access_url',
            'timestamp',
        )
        
        read_only_fields = fields
    
    def get_ephemeral_access_url(self, obj):
        """Retourne l'URL d'accès"""
        return obj.get_ephemeral_access_url()


class EphemeralEventAccessSerializer(serializers.Serializer):
    """
    Serializer pour accéder à un événement éphémère via son code d'accès.
    
    Endpoint : GET /api/events/ephemeral/{access_code}
    """
    
    access_code = serializers.CharField(
        required=True,
        max_length=50,
        help_text="Code d'accès unique de l'événement éphémère"
    )
    
    def validate_access_code(self, value):
        """Valide que le code d'accès existe"""
        from apps.events.models import Event
        
        try:
            event = Event.ephemeral.by_access_code(value)
            if not event:
                raise ValidationError(
                    "Code d'accès invalide ou événement introuvable.",
                    code='invalid_access_code'
                )
            return value
        except Exception as e:
            logger.error(f"Erreur validation code d'accès : {e}")
            raise ValidationError(
                "Erreur lors de la validation du code d'accès.",
                code='validation_error'
            )