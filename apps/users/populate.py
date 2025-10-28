# -*- coding: utf-8 -*-
"""
Created on June 15 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
import random
import string
import unicodedata

from faker import Faker

from apps.organizations.models import SubscriptionType
from apps.users.models import User, AppRole
from apps.users.serializers import UserSerializer
from apps.xlib.enums import AppRolesEnum, AppRolesDescriptionEnum

myFactory = Faker(['fr-FR', 'en-GB'])


def strip_accents(s):
    return str(''.join(c for c in unicodedata.normalize('NFD', s)
                       if unicodedata.category(c) != 'Mn')).translate({ord(c): None for c in string.whitespace})


subscription_types = [
    {
        'name': "Hebdomadaire",
        'price': 999.99,
        'order': 1,
        'validity_days_range': 7,
    },
    {
        'name': "Mensuel",
        'price': 2499.99,
        'order': 2,
        'validity_days_range': 30,
    },
    {
        'name': "Trimestriel",
        'price': 3999.99,
        'order': 3,
        'validity_days_range': 90,
    },
]

COUNTRY_CHOICES = ["226", "257", "229", "237", "242", "243", "225", "253",
                   "241" "224", "240", "261", "223", "227", "250", "236", "248", "221", "235", "228"]


def populate_admin_user_model():
    try:
        User.objects.create_superuser(email="admin@wuloevents.com", password="admin", first_name="Admin",
                                      last_name="Admin", conf_num='69196638', admin_id='69196638')
    except:
        pass


def populate_app_role_model():
    for value in AppRolesEnum.values():
        data = {
            'name': AppRolesDescriptionEnum[value].value,
            'label': value,
        }
        AppRole.objects.get_or_create(label=value, defaults=data)


def populate_user_model():
    for index in range(1, 20):
        phone = f'+{COUNTRY_CHOICES[random.randint(1, len(COUNTRY_CHOICES) - 1)]}6060{random.randint(1000, 9999)}'
        gender = random.choice(["M", "F"])
        first_name = myFactory.first_name_male() if gender == "M" else myFactory.first_name_female()
        last_name = myFactory.last_name()
        email = f"{first_name}.{last_name}@{myFactory.domain_name()}"
        data = {
            "first_name": str(first_name).strip(),
            "last_name": str(last_name).strip(),
            "email": strip_accents(str(email).lower()),
            "phone": phone,
            "password": strip_accents(str(email).lower())
        }

        print(data)
        serializer = UserSerializer(data=data)
        try:
            if serializer.is_valid(raise_exception=False):
                instance = serializer.save()
                if myFactory.boolean(chance_of_getting_true=75):
                    instance.validate()
        except Exception as e:
            print(e)


def populate_subscription_type_model():
    if not SubscriptionType.objects.all().exists():
        for element in subscription_types:
            SubscriptionType.objects.get_or_create(name=element["name"], defaults=element)

    if __name__ == '__main__':
        # populate_user_model()
        pass
