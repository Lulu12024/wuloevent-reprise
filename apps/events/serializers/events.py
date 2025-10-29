# -*- coding: utf-8 -*-
"""
Created on June 08, 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import datetime
import logging

import pytz
from drf_spectacular.utils import extend_schema_field

from apps.chat_rooms.models.room import ChatRoom
from apps.xlib.enums import ChatRoomTypeEnum, ChatRoomVisibilityEnum

utc = pytz.UTC
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.events.models import (
    EventType,
    Event,
)
from apps.events.serializers.types import EventTypeSerializer
from apps.organizations.models import Organization
from apps.organizations.serializers import OrganizationSerializerLight
from apps.users.serializers import UserSerializerLight
from apps.utils.models import Country
from apps.xlib.error_util import ErrorUtil, ErrorEnum

User = get_user_model()

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class EventCreationSerializer(serializers.ModelSerializer):
    type = serializers.PrimaryKeyRelatedField(
        queryset=EventType.objects.filter(active=True)
    )
    publisher = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True)
    )
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.filter(active=True)
    )
    country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True
    )
    autocreate_chatroom = serializers.BooleanField(required=False, default=True)
    participant_limit = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=15,
    )
    private = serializers.BooleanField(required=False, default=False)
    
    is_ephemeral = serializers.BooleanField(required=False, default=False)
    created_by_super_seller = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.filter(
            organization_type='SUPER_SELLER',
            active=True
        ),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Event
        fields = (
            "pk",
            "name",
            "description",
            "type",
            "default_price",
            "location_name",
            "location_long",
            "location_lat",
            "hour",
            "date",
            "cover_image",
            "publisher",
            "organization",
            "participant_count",
            "country",
            "have_passed_validation",
            "participant_limit",
            "private",
            "autocreate_chatroom",
            "is_ephemeral",               
            "created_by_super_seller", 
        )
        write_only_fields = ["autocreate_chatroom"]

    def create(self, validated_data):
        should_create_chatroom = validated_data.pop('autocreate_chatroom', True)
        is_ephemeral = validated_data.get('is_ephemeral', False)  # AJOUT

        instance = super().create(validated_data)
        instance.save()

        # ========== AJOUT : Générer le code d'accès pour événements éphémères ==========
        if is_ephemeral:
            instance.generate_ephemeral_access_code()
        # ========== FIN AJOUT ==========

        # Ne pas créer de chatroom pour les événements éphémères
        if should_create_chatroom and not is_ephemeral:  # MODIFICATION
            name = validated_data.get("name")
            ChatRoom.objects.create(
                title=f"Salon {name}",
                type=ChatRoomTypeEnum.PRIMARY.value,
                visibility=ChatRoomVisibilityEnum.PUBLIC.value,
                event=instance,
                cover_image=instance.cover_image
            )

        return instance

    def validate(self, attrs):
        data = super().validate(attrs)
        hour = data.get("hour", None)
        date = data.get("date", None)

        current_datetime = timezone.now()

        if self.instance:
            if date is None and hour is None:
                return data
            else:
                if date is None:
                    date = self.instance.date
                if hour is None:
                    hour = self.instance.hour
            event_datetime = timezone.make_aware(
                datetime.datetime.combine(date, hour), timezone.get_default_timezone()
            )
            if current_datetime >= event_datetime:
                raise ValidationError(
                    ErrorUtil.get_error_detail(ErrorEnum.EVENT_PAST_DATE),
                    code=ErrorEnum.EVENT_PAST_DATE.value,
                )

        else:
            if not hour:
                hour = datetime.time(00, 00, 00)

            event_datetime = timezone.make_aware(
                datetime.datetime.combine(date, hour), timezone.get_default_timezone()
            )
            if current_datetime >= event_datetime:
                raise ValidationError(
                    ErrorUtil.get_error_detail(ErrorEnum.CANNOT_ADD_EVENT_ON_PASS_DATE),
                    code=ErrorEnum.CANNOT_ADD_EVENT_ON_PASS_DATE.value,
                )
        
        participant_count = attrs.get('participant_count')
        participant_limit = attrs.get('participant_limit')
        
        if participant_count is not None and participant_limit is not None:
            if participant_count > participant_limit:
                raise ValidationError(
                    ErrorUtil.get_error_detail(ErrorEnum.PARTICIPANT_COUNT_EXCEEDS_LIMIT),
                    code=ErrorEnum.PARTICIPANT_COUNT_EXCEEDS_LIMIT.value,
                )

        # ========== Validation pour événements éphémères ==========
        is_ephemeral = attrs.get('is_ephemeral', False)
        organization_id = attrs.get('organization')
        
        if is_ephemeral:
            # Vérifier que l'organisation est un super-vendeur vérifié
            try:
                organization = Organization.objects.get(pk=organization_id)
                
                # Vérifier que c'est un super-vendeur
                if not organization.is_super_seller():
                    raise ValidationError({
                        'is_ephemeral': 'Seuls les super-vendeurs peuvent créer des événements éphémères.'
                    })
                
                # Vérifier que le super-vendeur est vérifié (KYC)
                if not organization.is_super_seller_verified():
                    raise ValidationError({
                        'is_ephemeral': 'Le super-vendeur doit être vérifié (KYC validé) pour créer des événements éphémères.'
                    })
                
                # Définir automatiquement created_by_super_seller
                attrs['created_by_super_seller'] = organization
                
            except Organization.DoesNotExist:
                raise ValidationError({
                    'organization': 'Organisation introuvable.'
                })
        # ========== FIN ==========
        return data


    def validate_participant_limit(self, value):
        DEFAULT_LIMIT = 15
        value = value if value is not None else DEFAULT_LIMIT
        organization_id = self.initial_data.get("organization")
        organization: Organization = Organization.objects.filter(pk=organization_id, active=True).first()

        if value > DEFAULT_LIMIT and not organization.have_active_subscription:
            raise ValidationError(
                f"{ErrorUtil.get_error_detail(ErrorEnum.CANNOT_UPDATE_PARTICIPANT_LIMIT_WITHOUT_ACTIVE_SUBSCRIPTION)} "
                f"(Le nombre maximal de participants sans abonnement actif est {DEFAULT_LIMIT})",
                code=ErrorEnum.CANNOT_UPDATE_PARTICIPANT_LIMIT_WITHOUT_ACTIVE_SUBSCRIPTION.value,
            )

        return value

    # class LightEventSerializer(GeoFeatureModelSerializer):


class LightEventSerializer(serializers.ModelSerializer):
    type = EventTypeSerializer()
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.filter(active=True)
    )
    is_user_favourite = serializers.SerializerMethodField()
    country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True
    )

    is_ephemeral = serializers.BooleanField(read_only=True)
    ephemeral_access_code = serializers.CharField(read_only=True)
    ephemeral_access_url = serializers.SerializerMethodField()

    @extend_schema_field(serializers.BooleanField)
    def get_is_user_favourite(self, obj):
        request = self.context.get("request", None)
        if request and request.user and request.user.is_authenticated:
            return obj.check_if_user_favourite(user=request.user)
        return None

    @extend_schema_field(serializers.BooleanField)
    def get_is_user_favourite(self, obj):
        request = self.context.get("request", None)
        if request and request.user and request.user.is_authenticated:
            return obj.check_if_user_favourite(user=request.user)
        return None

    # ========== NOUVELLE MÉTHODE ==========
    @extend_schema_field(serializers.CharField)
    def get_ephemeral_access_url(self, obj):
        """Retourne l'URL d'accès pour les événements éphémères"""
        if obj.is_ephemeral:
            return obj.get_ephemeral_access_url()
        return None
    
    class Meta:
        model = Event
        fields = (
            "pk",
            "name",
            "description",
            "type",
            "default_price",
            "views",
            "location_name",
            "location_lat",
            "location_long",
            "country",
            "have_passed_validation",
            "valid",
            "hour",
            "date",
            "cover_image",
            "is_user_favourite",
            "organization",
            "participant_count",

            "is_ephemeral",
            "ephemeral_access_code",
            "ephemeral_access_url",
        )


class EventSerializer(serializers.ModelSerializer):
    type = EventTypeSerializer()
    publisher = UserSerializerLight()
    organization = OrganizationSerializerLight()
    is_user_favourite = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    highlight_level = serializers.SerializerMethodField()
    country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True
    )

    is_ephemeral = serializers.BooleanField(read_only=True)
    created_by_super_seller = OrganizationSerializerLight(read_only=True)
    ephemeral_access_code = serializers.CharField(read_only=True)
    ephemeral_access_url = serializers.SerializerMethodField()

    @extend_schema_field(serializers.BooleanField)
    def get_is_user_favourite(self, obj):
        request = self.context.get("request", None)
        if request and request.user and request.user.is_authenticated:
            return obj.check_if_user_favourite(user=request.user)
        return None

    @extend_schema_field(serializers.FloatField)
    def get_distance(self, obj):
        try:
            return obj.distance.km
        except Exception as exc:
            pass

        return None

    def get_highlight_level(self, obj) -> int:
        try:
            return obj.highlight_level
        except Exception as exc:
            pass
        return 0

    @extend_schema_field(serializers.CharField)
    def get_ephemeral_access_url(self, obj):
        """Retourne l'URL d'accès pour les événements éphémères"""
        if obj.is_ephemeral:
            return obj.get_ephemeral_access_url()
        return None
    
    class Meta:
        model = Event
        fields = (
            "pk",
            "name",
            "description",
            "highlight_level",
            "type",
            "default_price",
            "views",
            "location_name",
            "location_lat",
            "location_long",
            "distance",
            "have_passed_validation",
            "valid",
            "hour",
            "date",
            "cover_image",
            "is_user_favourite",
            "publisher",
            "organization",
            "participant_count",
            "country",
            "expiry_date",
            "is_ephemeral",
            "created_by_super_seller",
            "ephemeral_access_code",
            "ephemeral_access_url",
        )
        read_only_fields = ['ephemeral_access_code', 'ephemeral_access_url']

    def get_ephemeral_access_url(self, obj):
        """Retourne l'URL d'accès pour les événements éphémères"""
        return obj.get_ephemeral_access_url()
    

class EphemeralEventSerializer(serializers.ModelSerializer):
    """
    Serializer pour les événements éphémères.
    Utilisé pour récupérer un événement via son code d'accès.
    """
    type = EventTypeSerializer(read_only=True)
    organization = OrganizationSerializerLight(read_only=True)
    created_by_super_seller = OrganizationSerializerLight(read_only=True)
    
    class Meta:
        model = Event
        fields = (
            "pk",
            "name",
            "description",
            "type",
            "default_price",
            "location_name",
            "location_lat",
            "location_long",
            "hour",
            "date",
            "cover_image",
            "organization",
            "created_by_super_seller",
            "ephemeral_access_code",
            "expiry_date",
        )
        read_only_fields = fields  # Tous les champs en lecture seule

