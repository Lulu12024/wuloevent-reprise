# -*- coding: utf-8 -*-
"""
Created on August 17 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from apps.notifications.models import (
    MobileDevice,
    NotificationType,
    SubscriptionToNotificationType,
    Notification,
)

User = get_user_model()

logger = logging.getLogger(__name__)


class UserDeviceTokensSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    phoneNumber = serializers.CharField(source='user.phone', read_only=True)
    deviceTokens = serializers.SerializerMethodField()
    
    class Meta:
        model = MobileDevice
        fields = ('email', 'phoneNumber', 'deviceTokens')
    
    def get_deviceTokens(self, obj):
        user_devices = MobileDevice.objects.filter(
            user=obj.user,
        ).order_by('-updated')
        
        device_tokens = []
        for device in user_devices:
            device_tokens.append({
                "pk": str(device.pk),
                "token": device.registration_id or device.token,
                "platform": device.type,
                "createdAt": device.timestamp if getattr(device, 'timestamp', None) else None,
                "lastUsed": device.updated if getattr(device, 'updated', None) else None,
            })
        
        return device_tokens


class MobileDeviceSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True), required=False, default=None
    )

    class Meta:
        model = MobileDevice
        fields = (
            "pk",
            "user",
            "name",
            "type",
            "token",
            "registration_id",
            "current_location_lat",
            "current_location_long",
            "active",
        )
        validators = [
            UniqueTogetherValidator(
                message='Un appareil mobile existe déjà avec ces informations',
                queryset=MobileDevice.objects.all(),
                fields=['registration_id', 'token']
            )
        ]
        read_only_fields = ("active",)

    def create(self, validated_data):
        token = validated_data.get("token")
        registration_id = validated_data.get("registration_id")

        try:
            mobile_device = MobileDevice.objects.get(token=token)
            if "anonymous" in mobile_device.registration_id:
                mobile_device.registration_id = registration_id
                mobile_device.save(update_fields=["registration_id"])
                return mobile_device
        except Exception as exc:
            logger.warning(exc)

        return super(MobileDeviceSerializer, self).create(validated_data)


class SubscriptionToNotificationTypeSerializer(serializers.ModelSerializer):
    notification_type = serializers.PrimaryKeyRelatedField(
        queryset=NotificationType.objects.all()
    )
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True)
    )

    class Meta:
        model = SubscriptionToNotificationType
        fields = ("notification_type", "user")


class NotificationSerializer(serializers.ModelSerializer):
    type_name = serializers.CharField(
        source="type.name", read_only=True
    )
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True)
    )
    type = serializers.PrimaryKeyRelatedField(
        queryset=NotificationType.objects.filter(active=True)
    )

    class Meta:
        model = Notification
        fields = (
            "pk",
            "type",
            "type_name",
            "user",
            "status",
            "title",
            "message",
            "data",
            "extra_data",
            "channels",
            "icon",
            "image",
            "unread",
            "timestamp",
            "scheduled_to_delivery",
        )

        extra_kwargs = {
            "status": {"read_only": True},
            "unread": {"read_only": True},
            "timestamp": {"read_only": True},
            "type_name": {"read_only": True},
            "extra_data": {"write_only": True},
        }
