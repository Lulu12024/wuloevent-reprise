# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.db import connection
from django.db.models import Q
from django_softdelete.models import SoftDeleteManager

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


def update_subscription_status(object):
    return object.active


class OrganisationManager(SoftDeleteManager):

    def list_by_user(self, user):
        objects = super().get_queryset().filter(
            Q(owner=user) | Q(memberships__user=user, memberships__is_deleted=False)).distinct()
        return objects

    def get_queryset(self):
        return super().get_queryset().prefetch_related('owner')


class SubscriptionManager(SoftDeleteManager):

    def update_status(self):
        from multiprocessing import cpu_count
        from multiprocessing.dummy import Pool as ThreadPool

        objects = super().get_queryset()
        all_tables = connection.introspection.table_names()
        if len(all_tables) > 0 and 'organizations_subscription' in all_tables:
            pool = ThreadPool(cpu_count())
            results = pool.map(update_subscription_status, objects)
            pool.close()
            pool.join()

        return objects
