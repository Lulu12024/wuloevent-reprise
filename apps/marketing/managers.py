# -*- coding: utf-8 -*-
"""
Created on  October 14 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from django_softdelete.models import SoftDeleteManager


class DiscountManager(SoftDeleteManager):

    def get_queryset(self):
        # return super(SoftDeleteManager, self).get_queryset().select_related("usage_rule").select_related(
        #     "validation_rule")
        return super(SoftDeleteManager, self).get_queryset()
