# -*- coding: utf-8 -*-

import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

import logging

from django.contrib import auth
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import Group
from django.db import models
from django.db.models import ExpressionWrapper, BooleanField, Q
from django.utils.translation import gettext_lazy as _
from commons.constants.user import DEFAULT_ANONYMOUS_FIRST_NAME, DEFAULT_ANONYMOUS_LAST_NAME, DEFAULT_ANONYMOUS_PASSWORD

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


class GlobalManager(models.Manager):

    def get_queryset(self):
        return super(GlobalManager, self).get_queryset().annotate(
            is_event_organizer=ExpressionWrapper(Q(organizations_own__isnull=False), output_field=BooleanField()))


class CustomUserManager(BaseUserManager):
    use_in_migrations = True
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def get_queryset(self):
        return super(CustomUserManager, self).get_queryset().filter(deactivated_at__isnull=True).annotate(
            is_event_organizer=ExpressionWrapper(Q(organizations_own__isnull=False),
                                                 output_field=BooleanField())).annotate(
            belong_to_an_organization=ExpressionWrapper(Q(Q(is_event_organizer=True) | Q(memberships__isnull=False)),
                                                        output_field=BooleanField())).distinct()

    def create_user(self, email, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError("Adresse mail manquante")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        group, created = Group.objects.get_or_create(name='Admin')
        user.groups.add(group)

        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_app_admin', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)

    def get_or_create_anonymous_user(self, email, phone=None, **extra_fields):

        # Todo: Supposing the account was deleted, propose a flow to restore it
        try:
            query = Q()
            if email:
                query |= Q(email=email)
            if phone:
                query |= Q(phone=phone)
            
            user = self.select_related("country").filter(query).first()
            if not user:
                raise self.model.DoesNotExist
            return user
        except self.model.DoesNotExist:
            return self.create_anonymous_user(email, phone=phone, **extra_fields)

    def create_anonymous_user(self, email, phone=None, **extra_fields):
        """
        Create and save an anonymous according to wuloevent business logic with an auto-given full name and password.

        """
        #  Setting default first name and last name from env

        extra_fields.setdefault('first_name', os.environ.get("DEFAULT_ANONYMOUS_FIRST_NAME",DEFAULT_ANONYMOUS_FIRST_NAME))
        extra_fields.setdefault('last_name', os.environ.get("DEFAULT_ANONYMOUS_LAST_NAME",DEFAULT_ANONYMOUS_LAST_NAME))
        extra_fields.setdefault('password', os.environ.get("DEFAULT_ANONYMOUS_PASSWORD",DEFAULT_ANONYMOUS_PASSWORD))
        extra_fields.setdefault('is_active', True)

        return self.create_user(email, phone=phone, **extra_fields)

    def with_perm(self, perm, is_active=True, include_superusers=True, backend=None, obj=None):
        if backend is None:
            backends = auth._get_backends(return_tuples=True)
            if len(backends) == 1:
                backend, _ = backends[0]
            else:
                raise ValueError(
                    'You have multiple authentication backends configured and '
                    'therefore must provide the `backend` argument.'
                )
        elif not isinstance(backend, str):
            raise TypeError(
                'backend must be a dotted import path string (got %r).'
                % backend
            )
        else:
            backend = auth.load_backend(backend)
        if hasattr(backend, 'with_perm'):
            return backend.with_perm(
                perm,
                is_active=is_active,
                include_superusers=include_superusers,
                obj=obj,
            )
        return self.none()
