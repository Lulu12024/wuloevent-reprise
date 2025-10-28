# -*- coding: utf-8 -*-
"""
Created on 25/07/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, UpdateModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet as DefaultReadOnlyModelViewSet

from apps.organizations.mixings import CheckParentPermissionMixin
from apps.utils.utils.baseviews import BaseModelMixin

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


class WriteOnlyNestedModelViewSet(CheckParentPermissionMixin, CreateModelMixin, UpdateModelMixin, DestroyModelMixin,
                                  BaseModelMixin, GenericViewSet):
    """
    A views set that provides default `create()`, destroy(), and `update()` actions.
    """
    pass


class ReadOnlyModelViewSet(BaseModelMixin, DefaultReadOnlyModelViewSet):
    """
    A views set that provides default `list()`, retrieve(), actions.
    """
    pass
