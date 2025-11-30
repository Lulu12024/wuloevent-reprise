# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import datetime
import logging

from django.db.models import DateTimeField, F, IntegerField, Sum, Value
from django.db.models.expressions import ExpressionWrapper, Func
from django.db.models.functions import Coalesce, Cast
from django_softdelete.models import SoftDeleteManager

from apps.utils.managers import GeoModelManager

logger = logging.getLogger(__name__)
logger.setLevel('INFO')

TIMESTAMP_DIFFERENCE = 3600


def update_event_highlighting_status(obj):
    try:
        return obj.active
    except Exception as exc:
        logger.exception(exc.__str__())


class EventHighlightingManager(SoftDeleteManager):

    def get_queryset(self):
        # from multiprocessing import cpu_count
        # from multiprocessing.dummy import Pool as ThreadPool
        #
        # objects = super().get_queryset()
        # all_tables = connection.introspection.table_names()
        #
        # if len(all_tables) > 0 and 'users_subscription' in all_tables:
        #     pool = ThreadPool(cpu_count())
        #     results = pool.map(update_event_highlighting_status, objects)
        #     pool.close()
        #     pool.join()
        #
        # return objects
        return super(EventHighlightingManager, self).get_queryset()


class Epoch(Func):
    template = 'EXTRACT(epoch FROM %(expressions)s)::INTEGER'
    output_field = IntegerField()


class EventManager(GeoModelManager):

    def get_queryset(self):
        return super(GeoModelManager, self).get_queryset().select_related("type").select_related(
            "publisher").select_related("organization").select_related("country").filter(active=True).annotate(
            start_datetime=ExpressionWrapper(F('date') + F('hour'), output_field=DateTimeField())).annotate(
            highlight_level=Coalesce(Sum(F('highlight__type__order') * Cast('highlight__active_status', IntegerField()),
                                         output_field=IntegerField()), 0)).annotate(
            time_before_start=Epoch(F('start_datetime') - Value(datetime.datetime.now())) - Value(
                TIMESTAMP_DIFFERENCE)).order_by(
            'highlight_level').order_by(
            'time_before_start')


class AdminEventManager(GeoModelManager):

    def get_queryset(self):
        queryset = super(GeoModelManager, self).get_queryset().select_related("type").select_related(
            "publisher").select_related("organization").select_related("country").annotate(
            start_datetime=ExpressionWrapper(F('date') + F('hour'), output_field=DateTimeField())).annotate(
            highlight_level=Coalesce(Sum(F('highlight__type__order') * Cast('highlight__active_status', IntegerField()),
                                         output_field=IntegerField()), 0)).annotate(
            time_before_start=Epoch(F('start_datetime') - Value(datetime.datetime.now())) - Value(
                TIMESTAMP_DIFFERENCE)).order_by('time_before_start')
        queryset.from_admin = True
        return queryset
