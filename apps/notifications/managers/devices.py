# -*- coding: utf-8 -*-
"""
Created on August 17, 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
from datetime import datetime, timedelta
from typing import TypedDict

from django.db.models import Q

from apps.utils.managers import GeoModelManager


def query_filter_maker(data_field_querier, time):
    q = Q(**{f'notifications_history__notification__data__{data_field_querier["field_name"]}': data_field_querier[
        'field_value'], 'notifications_history__timestamp__gte': time})
    return q


class MobileDeviceManager(GeoModelManager):
    class DataFieldQueryType(TypedDict):
        field_name: str
        field_value: any

    def filter_notified_about_field_in_data_and_time_since(self, data_field_querier: DataFieldQueryType,
                                                           time_since: int, negation: bool = False):
        """
        Args:
        data_field_querier: dict containing {field_name: str, field_value: any }
        time_since: time since notification was sent in hour
        """
        time = datetime.now() - timedelta(hours=time_since)
        return super().get_queryset().filter(
            ~query_filter_maker(data_field_querier, time)).distinct() if negation else super().get_queryset().filter(
            query_filter_maker(data_field_querier, time)).distinct()


"""



MobileDevice.objects.filter_notified_about_field_in_data_and_time_since(data_field_querier={'field_name': 'eventId', 'field_value': 703}, time_since=1, negation = True)

from apps.notifications.models import MobileDevice
"""
