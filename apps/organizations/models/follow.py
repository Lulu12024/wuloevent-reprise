# -*- coding: utf-8 -*-
"""
Created on July 13, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.db import models

from apps.organizations.models.organizations import Organization
from commons.models import AbstractCommonBaseModel

# Create your models here.

logger = logging.getLogger(__name__)


class OrganizationFollow(AbstractCommonBaseModel):
    follower = models.ForeignKey("users.User", on_delete=models.CASCADE, null=True,
                                 blank=True, related_name='me_following_organizations')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True,
                                     blank=True, related_name='users_followings_me')

    def __str__(self) -> str:
        return f'Follower: {self.follower.get_full_name()}  / Organization: {self.followed.get_full_name()}'

    class Meta:
        verbose_name = "Suivi d' un organization"
        verbose_name_plural = "Suivis d' une organization"
        # unique_together = ('follower', 'followed')
