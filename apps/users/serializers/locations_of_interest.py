# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.contrib.gis.geos import Point
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from apps.users.models import (
    PointOfInterest,
    User,
    ZoneOfInterest,
)

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class PointOfInterestSerializer(GeoFeatureModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = PointOfInterest
        geo_field = "location"
        fields = (
            "pk",
            "user",
            "location",
            "location_long",
            "location_lat",
            "approximate_distance",
            "allow_notifications",
            "timestamp",
            "active",
        )

    def create(self, validated_data):
        long = validated_data.get("location_long", 0.0)
        lat = validated_data.get("location_lat", 0.0)
        instance = super().create(validated_data)
        location = Point(lat, long, srid=4326)
        instance.location = location
        instance.save()
        return instance


class ZoneOfInterestSerializer(GeoFeatureModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = ZoneOfInterest
        geo_field = "geofence"
        fields = (
            "pk",
            "user",
            "geofence",
            "allow_notifications",
            "timestamp",
            "active",
        )
