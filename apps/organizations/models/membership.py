# -*- coding: utf-8 -*-
"""
Created on July 13, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from django.db import models

from apps.organizations.models.organizations import Organization
from apps.organizations.models.roles import Role
from commons.models import AbstractCommonBaseModel

# Create your models here.

logger = logging.getLogger(__name__)


class OrganizationMembership(AbstractCommonBaseModel):
    organization = models.ForeignKey(verbose_name="Organisation d' appartenance", to=Organization,
                                     on_delete=models.CASCADE, null=True,
                                     blank=True, related_name='memberships')
    user = models.ForeignKey(verbose_name="Utilisateur", to="users.User", on_delete=models.CASCADE, null=True,
                             blank=True, related_name='memberships')
    # rights = models.JSONField(verbose_name="Droits", default={'data': []})
    roles = models.ManyToManyField(to=Role, verbose_name="Roles du membre")

    class Meta:
        verbose_name = "Membre d' une organisation"
        verbose_name_plural = "Membres d' une organisation"
        unique_together = ('user', 'organization',)

    def __str__(self) -> str:
        return f'Membre {self.user.get_full_name()} de l\' organisation {self.organization.name}'

    def save(self, *args, **kwargs) -> None:
        if self.organization.owner == self.user:
            raise ValueError(
                'Vous êtes le propriétaire de cette organisation.')
        return super().save(*args, **kwargs)
