# -*- coding: utf-8 -*-
"""
Created on July 11, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging
from string import digits

from django.db import models
from django.utils.crypto import get_random_string

from apps.notifications.signals.initializers import send_email_signal
from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


class AccountValidationRequest(AbstractCommonBaseModel):
    class Meta:
        verbose_name = "Requête de Validation de Compte"
        verbose_name_plural = "Requêtes de Validation de Compte"

    def send_verification_code(self):
        code = get_random_string(length=6, allowed_chars=digits)
        send_email_signal.send(sender='send_verification_code', instance=self,
                               email_data={
                                   "params": {
                                       "email": self.user.email,
                                       'full_name': self.user.get_full_name(),
                                       'code': code
                                   },
                                   "email_type": 'account_validation_request'}
                               )
        return code

    def re_send_verification_code(self):
        code = get_random_string(length=6, allowed_chars=digits)
        send_email_signal.send(sender='re_send_verification_code', instance=self,
                               email_data={
                                   "params": {
                                       "email": self.user.email,
                                       'full_name': self.user.get_full_name(),
                                       'code': code
                                   },
                                   "email_type": 'account_validation_request'}
                               )
        self.code = code
        self.save()

    user = models.ForeignKey(
        to="users.User",
        related_name='account_validation_requests',
        on_delete=models.CASCADE,
        verbose_name="Utilisateur"
    )

    # Key field, though it is not the primary key of the model
    code = models.CharField(
        verbose_name="Code",
        max_length=64,
        db_index=True,
        unique=True
    )

    ip_address = models.GenericIPAddressField(
        verbose_name="Adresse IP de la session",
        default="",
        blank=True,
        null=True,
    )
    user_agent = models.CharField(
        max_length=256,
        verbose_name="HTTP User Agent",
        default="",
        blank=True,
    )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.send_verification_code()
            self.user.set_conf_num(self.code)
        return super(AccountValidationRequest, self).save(*args, **kwargs)

    def __str__(self) -> str:
        return "Account validation request for  {user}".format(user=self.user)


class ResetPasswordRequest(AbstractCommonBaseModel):
    class Meta:
        verbose_name = "Requête de Modification de Mot de Passe"
        verbose_name_plural = "Requêtes de Modification de Mot de Passe"

    def send_verification_code(self):
        code = get_random_string(length=6, allowed_chars=digits)
        send_email_signal.send(sender='send_verification_code', instance=self,
                               email_data={
                                   "params": {
                                       "user_id": str(self.user_id),
                                       "email": self.user.email,
                                       'full_name': self.user.get_full_name(),
                                       'code': code
                                   },
                                   "email_type": 'password_reset_request'}
                               )
        return code

    def re_send_verification_code(self):
        code = get_random_string(length=6, allowed_chars=digits)
        send_email_signal.send(sender='re_send_verification_code', instance=self,
                               email_data={
                                   "params": {
                                       "user_id": str(self.user_id),
                                       "email": self.user.email,
                                       'full_name': self.user.get_full_name(),
                                       'code': code
                                   },
                                   "email_type": 'password_reset_request'}
                               )

        self.code = code
        self.save()

    user = models.ForeignKey(
        to="users.User",
        related_name='password_reset_requests',
        on_delete=models.CASCADE,
        verbose_name="Utilisateur"
    )

    # Key field, though it is not the primary key of the model
    code = models.CharField(
        verbose_name="Code",
        max_length=64,
        db_index=True,
        unique=True
    )

    ip_address = models.GenericIPAddressField(
        verbose_name="Adresse IP de la session",
        default="",
        blank=True,
        null=True,
    )
    user_agent = models.CharField(
        max_length=256,
        verbose_name="HTTP User Agent",
        default="",
        blank=True,
    )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.send_verification_code()
        return super(ResetPasswordRequest, self).save(*args, **kwargs)

    def __str__(self) -> str:
        return "Password reset token for user {user}".format(user=self.user)
