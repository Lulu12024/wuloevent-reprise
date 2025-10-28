# -*- coding: utf-8 -*-
"""
Created on June 05, 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import APIException

from apps.events.models import (
    Event,
    TicketCategoryFeature,
    TicketCategory,
    Ticket,
)
from apps.organizations.models import Organization
from apps.xlib.error_util import ErrorUtil, ErrorEnum

User = get_user_model()

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class TicketCategoryFeatureSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.filter(active=True), required=False, default=None
    )

    class Meta:
        model = TicketCategoryFeature
        fields = (
            "pk",
            "organization",
            "description",
            "active",
        )

    def validate_organization(self, value):
        return self.context["request"].organization


class AddFeaturesToTicketCategorySerializer(serializers.Serializer):
    ticket_category = serializers.PrimaryKeyRelatedField(
        queryset=TicketCategory.objects.filter(active=True)
    )
    features = serializers.PrimaryKeyRelatedField(
        queryset=TicketCategoryFeature.objects.filter(active=True), many=True
    )

    class Meta:
        fields = ("ticket_category", "features")

    def create(self, validated_data):
        ticket_category = self.validated_data.get("ticket_category")
        features = self.validated_data.get("features")
        for feature in features:
            ticket_category.features.add(feature)
        ticket_category.save()
        return ticket_category


class LightTicketSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=TicketCategory.objects.filter(active=True))

    class Meta:
        model = Ticket
        fields = (
            "pk",
            "name",
            "category",
            "description",
            "price",
            "expiry_date"
        )


class TicketSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.filter(active=True), required=False, default=None
    )
    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())
    category = serializers.PrimaryKeyRelatedField(
        queryset=TicketCategory.objects.filter(active=True),
        required=False,
        allow_null=True,
        default=None,
    )

    class Meta:
        model = Ticket
        fields = (
            "pk",
            "name",
            "organization",
            "event",
            "category",
            "description",
            "price",
            "expiry_date",
            "initial_quantity",
            "available_quantity",
        )

        extra_kwargs = {
            "active": {"read_only": True},
        }

        # validators = [
        #     UniqueTogetherValidator(
        #         queryset=Ticket.objects.all(),
        #         fields=['name', 'category__pk']
        #     )
        # ]

    def validate_organization(self, value):
        return self.context["request"].organization

    def validate_event(self, event):
        if not event.have_passed_validation:
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.EVENT_UNDERGOING_VALIDATION),
                code=ErrorEnum.EVENT_UNDERGOING_VALIDATION.value,
            )
        if not event.valid:
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.INVALID_EVENT_DATA),
                code=ErrorEnum.INVALID_EVENT_DATA.value,
            )
        return event


class TicketCategorySerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.filter(active=True), required=False, default=None
    )
    event = serializers.PrimaryKeyRelatedField(
        queryset=Event.objects.filter(active=True)
    )
    features = TicketCategoryFeatureSerializer(
        many=True, required=False, read_only=True
    )

    tickets = TicketSerializer(many=True, required=False, read_only=True)

    class Meta:
        model = TicketCategory
        fields = (
            "pk",
            "organization",
            "name",
            "event",
            "description",
            "tickets",
            "features",
            "active",
        )

    def validate_organization(self, value):
        return self.context["request"].organization

    def validate_event(self, event):
        if not event.have_passed_validation:
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.EVENT_UNDERGOING_VALIDATION),
                code=ErrorEnum.EVENT_UNDERGOING_VALIDATION.value,
            )
        if not event.valid:
            raise APIException(
                ErrorUtil.get_error_detail(ErrorEnum.INVALID_EVENT_DATA),
                code=ErrorEnum.INVALID_EVENT_DATA.value,
            )
        return event
