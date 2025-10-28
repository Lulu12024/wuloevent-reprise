# -*- coding: utf-8 -*-
"""
Created on July 11, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging
from string import digits
from typing import Literal
from uuid import uuid4

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string

from apps.notifications.signals.initializers import send_email_signal
from apps.users.managers import CustomUserManager, GlobalManager
from apps.utils.utils import _upload_to
from apps.utils.validators import PhoneNumberValidator

logger = logging.getLogger(__name__)
logger.setLevel('INFO')

SEX_CHOICES = (
    ("F", "Féminin"),
    ("M", "Masculin"),
    ("A", "Autres"),
)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False, unique=True)
    first_name = models.CharField(
        verbose_name='Prénoms', max_length=30)
    username = models.CharField(
        verbose_name='Username', max_length=30, null=True)
    last_name = models.CharField(
        verbose_name='Nom', max_length=150)
    email = models.EmailField(
        verbose_name='Adresse mail', blank=True, null=True)
    sex = models.CharField(verbose_name='Sexe', max_length=10,
                           choices=SEX_CHOICES, blank=True, null=False)
    role = models.ForeignKey(
        to="users.AppRole",
        related_name="associated_users",
        verbose_name="Role dans l' application de l' utilisateur",
        null=True, blank=True,
        on_delete=models.DO_NOTHING
    )
    birthday = models.DateField(
        verbose_name='Date de Naissance', blank=True, null=True)
    phone = models.CharField(verbose_name='Numéro de téléphone', max_length=25,
                             null=True, blank=True, validators=[PhoneNumberValidator()])
    country = models.ForeignKey(to='utils.Country', blank=True, null=True, verbose_name="Pays de résidence",
                                on_delete=models.SET_NULL)
    profile_image = models.ImageField(verbose_name='Image de profile', upload_to=_upload_to,
                                      blank=True,
                                      null=True)
    admin_id = models.CharField(
        verbose_name='Numéro de connection admin', max_length=128, unique=True)
    conf_num = models.CharField(
        verbose_name='Numéro de confirmation', max_length=128)

    password = models.CharField(
        verbose_name='Mot de passe', max_length=128, blank=False)
    is_active = models.BooleanField(
        verbose_name="Désigne si l' utilisateur est actif",
        default=True,
        help_text="Désigne si cet utilisateur doit être traité comme actif. Désélectionnez cette option au lieu de "
                  "supprimer les comptes. "
    )
    have_validate_account = models.BooleanField(
        verbose_name="Désigne si l' utilisateur a validé son compte",
        default=False
    )
    date_joined = models.DateTimeField(
        verbose_name="Date d' inscription", default=timezone.now)

    objects = CustomUserManager()
    global_objects = GlobalManager()
    is_staff = models.BooleanField(default=False, verbose_name="Désigne si l' utilisateur est un admin système")
    is_app_admin = models.BooleanField(default=False,
                                       verbose_name="Désigne si l' utilisateur est un admin Wulo Events")
    phone_number_validated = models.BooleanField(default=False,
                                                 verbose_name="Désigne si le numéro de téléphone est validé ")
    deactivated_at = models.DateTimeField(blank=True, null=True,
                                          verbose_name="Désigne la date de désactivation du compte")
    register_from = models.CharField(
        max_length=128, blank=True, null=True,
        verbose_name="Désigne la source d'inscription"
    )

    USERNAME_FIELD = 'admin_id'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'email']

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def eligible_for_reset(self):
        return self.have_validate_account

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    def set_phone(self, phone):
        self.phone = phone
        self.save()

    def set_conf_num(self, code):
        if code and code != '':
            self.conf_num = code
            self.save()
        else:
            raise ValueError('Le code de confirmation est vide.')

    def ask_verification(self):
        if not self.is_active:
            code = get_random_string(length=6, allowed_chars=digits)
            send_email_signal.send(sender='send_verification_code', instance=self,
                                   email_data={
                                       "params": {
                                           "user_id": str(self.pk),
                                           "email": self.email,
                                           'full_name': self.get_full_name(),
                                           'code': code
                                       },
                                       "email_type": 'account_validation_request'}
                                   )
            self.conf_num = code
            self.save()

    def validate(self):
        self.have_validate_account = True
        self.save()

    def save(self, *args, **kwargs):
        if self.admin_id == "" or not self.admin_id:
            self.admin_id = get_random_string(12)

        super(User, self).save(*args, **kwargs)

    def check_organization_access(self, organization, role='MEMBER'):
        membership_queryset = self.memberships.filter(
            organization=organization)
        if not membership_queryset.exists():
            return False
        total_weight = sum([int(element) for element in list(
            membership_queryset.first().roles.values_list('weight', flat=True))])
        if role == 'MEMBER':
            return total_weight >= 1
        if role == 'COORDINATOR':
            return total_weight >= 2

    def get_user_role_for_organization(self, organization) -> Literal["OWNER", "MEMBER", "COORDINATOR", None]:
        if organization.owner == self:
            return 'OWNER'
        membership_queryset = self.memberships.filter(
            organization=organization)
        if not membership_queryset.exists():
            return None
        total_weight = sum([int(element) for element in list(
            membership_queryset.first().roles.values_list('weight', flat=True))])
        if total_weight < 2:
            return 'MEMBER'
        if total_weight >= 2:
            return 'COORDINATOR'
        return None

    @property
    def has_app_admin_access(self):
        return self.is_app_admin and self.role

    @property
    def get_entity_info(self):
        return {"name": self.get_full_name()}

    def __str__(self) -> str:
        return f'{self.email} & {self.get_full_name()}'
