# -*- coding: utf-8 -*-
"""
Created on November 21, 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.db.models import F, Func
from django_softdelete.models import SoftDeleteManager

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class GeoModelManager(SoftDeleteManager):

    def annotate_spherical_distance(
            self,
            dynamic_location_fields,
            static_location,
    ):
        latitude_field_name, longitude_field_name = dynamic_location_fields
        latitude, longitude = static_location
        """
        Returns a QuerySet of locations annotated with their distance from the
        given point. This can then be filtered.
        Usage:
            Foo.objects.annotate_spherical_distance((lat_field, lon_field), (lat, lon)).filter(spherical_distance__lt=10).count()
        @see http://stackoverflow.com/a/31715920/1373318
        """

        class Sin(Func):
            function = "SIN"

        class Cos(Func):
            function = "COS"

        class Acos(Func):
            function = "ACOS"

        class Radians(Func):
            function = "RADIANS"

        radlat = Radians(latitude)  # given latitude
        radlong = Radians(longitude)  # given longitude
        radflat = Radians(F(latitude_field_name))
        radflong = Radians(F(longitude_field_name))

        # Note 3959.0 is for miles. Use 6371 for kilometers
        Expression = 6371.0 * Acos(
            Cos(radlat) * Cos(radflat) * Cos(radflong - radlong)
            + Sin(radlat) * Sin(radflat)
        )

        return self.get_queryset().annotate(spherical_distance=Expression)
