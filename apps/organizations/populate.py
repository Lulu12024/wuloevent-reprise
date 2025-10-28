# -*- coding: utf-8 -*-
"""
Created on June 15 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
import logging
import os
import random
import string
import tempfile
import unicodedata

from django.core.files import File
from faker import Faker

from apps.organizations.models import Role, Organization, OrganizationMembership, SubscriptionType
from apps.organizations.serializers import SubscriptionCreationSerializer
from apps.users.models import User, Transaction
from apps.xlib.enums import TransactionStatusEnum

logger = logging.getLogger(__name__)
logger.setLevel('INFO')

myFactory = Faker(['fr-FR', 'en-GB'])


def strip_accents(s):
    return str(''.join(c for c in unicodedata.normalize('NFD', s)
                       if unicodedata.category(c) != 'Mn')).translate({ord(c): None for c in string.whitespace})


def assert_admin_user_model_is_populated():
    return User.objects.filter(is_staff=True).count() > 0


def assert_user_model_is_populated():
    return User.objects.all().count() > 5


def assert_organization_model_is_populated():
    return Organization.objects.all().count() > 5


def get_random_object(objects):
    items = list(objects)
    return random.choice(items)


# populate_event_type_model()


def populate_role_model():
    for role_key in Role.ROLE_WEIGHT_NAME_MATCHER.keys():
        data = {'name': role_key,
                'weight': Role.ROLE_WEIGHT_NAME_MATCHER[role_key], 'description': role_key}
        Role.objects.get_or_create(name=role_key, defaults=data)


def populate_admin_organization():
    assert assert_admin_user_model_is_populated(), "Veuillez peupler le model admin utilisateur"

    try:
        name = "Organisation Admin "
        email = "admin@wuloevents.com"
        description = "Organisation admin pour pré-peupler les fixture de base ayant besoin " \
                      "d' une organization pour être peuplé",
        address = "Wulo Events, Gbegamey"
        owner = User.objects.filter(is_staff=True, email__icontains="admin@wuloevents.com").first()

        data = {
            'name': name,
            "email": email,
            'description': description,
            'address': address,
            'owner': owner
        }
        new_organization = Organization(**data)

        if os.path.exists('static/medias/test.png'):
            with open('static/medias/test.png', 'rb') as f:
                lf = tempfile.NamedTemporaryFile(dir='static/medias')
                lf.write(f.read())
                new_organization.logo.save(
                    f'file_{myFactory.sentence()[:8]}.jpeg', File(lf), save=True)
                lf.close()
        new_organization.save()
    except Exception as exc:
        pass
        logger.exception(exc.__str__())


def populate_organization_model(length=14):
    assert assert_user_model_is_populated(), "Veuillez populer le model utilisateur"
    for index in range(length):
        try:
            name = myFactory.sentence()[:random.randint(30, 70)]
            email = f"{name}@{myFactory.domain_name()}"
            description = myFactory.text()[:random.randint(700, 1000)],
            address = myFactory.address()
            owner = get_random_object(User.objects.filter(is_active=True))

            data = {
                'name': name,
                "email": strip_accents(str(email).lower()),
                'description': description,
                'address': address,
                'owner': owner
            }
            new_organization = Organization(**data)
            if os.path.exists('static/medias/test.png'):
                with open('static/medias/test.png', 'rb') as f:
                    # with ContentFile(f.read()) as f_content:
                    #    new_event.cover_image.save(
                    #        f'file_{myFactory.sentence()[:8]}.jpeg', f_content)

                    lf = tempfile.NamedTemporaryFile(dir='static/medias')
                    lf.write(f.read())
                    # doc object with file FileField.
                    new_organization.logo.save(
                        f'file_{myFactory.sentence()[:8]}.jpeg', File(lf), save=True)
                    lf.close()

            new_organization.save()
        except Exception as exc:
            pass
            logger.exception(exc.__str__())


def populate_organization_membership(length=50):
    assert assert_user_model_is_populated(), "Veuillez populer le model utilisateur"
    for index in range(length):
        try:
            organization = get_random_object(
                Organization.objects.filter(active=True))

            user = get_random_object(
                User.objects.filter(organizations_own__isnull=True))
            roles_pks = Role.objects.values_list('pk', flat=True)
            random_pk = random.choice(roles_pks)
            roles = Role.objects.filter(pk=random_pk)
            data = {
                'organization': organization,
                'user': user,
            }

            if not OrganizationMembership.objects.filter(user=user, organization=organization).exists():
                new_organization_membership = OrganizationMembership(**data)
                new_organization_membership.save()
                new_organization_membership.roles.set(roles)
                print(new_organization_membership)
        except Exception as exc:
            pass
            logger.exception(exc.__str__())


def populate_organizations_subscriptions():
    assert assert_organization_model_is_populated(), "Veuillez populer le model organisateurs"
    organizations = Organization.objects.all()
    for organization in organizations:
        if myFactory.boolean(chance_of_getting_true=80):
            try:

                unity_time_number = random.randint(1, 9)
                subscription_type = get_random_object(SubscriptionType.objects.all())

                data = {
                    'organization': organization.pk,
                    'subscription_type': subscription_type.pk,
                    'unity_time_number': unity_time_number
                }
                print(data)
                serializer = SubscriptionCreationSerializer(data=data)
                print(serializer.is_valid(raise_exception=True))
                if serializer.is_valid(raise_exception=False):
                    subscription = serializer.save()
                    print(subscription, 111111111111)
                    if myFactory.boolean(chance_of_getting_true=75):
                        print("Setting it to status active")
                        Transaction.objects.filter(entity_id=subscription.pk).update(
                            status=TransactionStatusEnum.RESOLVED.value)
            except Exception as exc:
                pass
                logger.exception(exc.__str__())


"""exec(open('apps/organization/populate.py').read())"""
