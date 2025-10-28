# -*- coding: utf-8 -*-
"""
Created on June 15 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
import datetime
import logging
import os
import random
import tempfile
from datetime import date

from dateutil.relativedelta import relativedelta
from django.core.files import File
from django.db import transaction
from faker import Faker

from apps.events.models import EventType, Event, EventHighlightingType, TicketCategory, Ticket
from apps.organizations.models import Organization

logger = logging.getLogger(__name__)
logger.setLevel('INFO')

myFactory = Faker(['fr-FR', 'en-GB'])


def get_random_object(objects):
    items = list(objects)
    return random.choice(items)


event_highlighting_type = [
    {
        'name': "Annuel",
        'price': 50000,
        'order': 1,
        'description': "7",
        "number_of_days_covered": 356
    },
    {
        'name': "Trimestriel",
        'price': 20000,
        'order': 1,
        'description': "30",
        "number_of_days_covered": 90
    },
    {
        'name': "Mensuel",
        'price': 10000,
        'order': 1,
        'description': "90",
        "number_of_days_covered": 30
    },
    {
        'name': "Hebdomadaire",
        'price': 3000,
        'order': 1,
        'description': "90",
        "number_of_days_covered": 7
    },
    {
        'name': "Influenceur Plus",
        'price': "99999",
        'order': 2,
        'description': "90",
        "number_of_days_covered": 7
    },
]


def populate_event_highlighting_type():
    for element in event_highlighting_type:
        EventHighlightingType.objects.get_or_create(name=element["name"], defaults=element)


event_types = [

    {
        'name': "Professionnels",
        'description': "Professionnels"
    },
    {
        'name': "Culturels & Artistiques",
        'description': "Culturels & Artistiques"
    }
    ,
    {
        'name': "Sociaux & Festifs",
        'description': "Sociaux & Festifs"
    }
    ,
    {
        'name': "Éducatifs",
        'description': "Éducatifs"
    }
    ,
    {
        'name': "Sportifs",
        'description': "Sportifs"
    },
    {
        'name': "Humanitaires & Associatifs",
        'description': "Humanitaires & Associatifs"
    },
    {
        'name': " Familles & Enfants",
        'description': " Familles & Enfants"
    },
    {
        'name': "Technologiques & Innovants",
        'description': "Technologiques & Innovants"
    },
    {
        'name': "Santé et Bien Etre",
        'description': "Santé et Bien Etre"
    }
    ,
    {
        'name': "Religieux & Spirituels",
        'description': "Religieux & Spirituels"
    }
    ,
    {
        'name': "Virtuels & Hybrides",
        'description': "Virtuels & Hybrides"
    }
    ,
    {
        'name': "Actualités & Infos",
        'description': "Actualités & Infos"
    }
    ,
    {
        'name': "Divers/Autres",
        'description': "Divers/Autres"
    }

]


def populate_event_type_model():
    with transaction.atomic():
        if not EventType.objects.all().exists():
            try:
                for element in event_types:
                    event_type = EventType.objects.get_or_create(name=element["name"], defaults=element)
                    print(event_type)
            except Exception as exc:
                logger.exception(exc.__str__())


# populate_event_type_model()


def populate_event_model(length=240):
    for index in range(length):
        try:
            type = get_random_object(EventType.objects.filter(active=True))
            location_name = myFactory.address()
            location_lat, location_long = myFactory.latlng()
            default_price = myFactory.pyint(min_value=5000)
            organization = get_random_object(Organization.objects.all())
            publisher = organization.owner
            earlier = date.today() + relativedelta(months=+8)

            hour = datetime.datetime.utcnow() + relativedelta(hours=random.randint(-7, +7))
            have_passed_validation = myFactory.boolean(chance_of_getting_true=75)
            data = {
                'name': myFactory.sentence()[:random.randint(30, 70)],
                'description': myFactory.text()[:random.randint(700, 1000)],
                'type': type,
                'location_name': location_name,
                'location_lat': location_lat,
                'location_long': location_long,
                'default_price': default_price,
                'hour': f'{hour.hour}:00',
                'date': myFactory.date_between(datetime.date.today(), earlier),
                'organization': organization,
                'publisher': publisher,
                'is_tickets_management_enabled': myFactory.boolean(chance_of_getting_true=75),
                'have_passed_validation': have_passed_validation,
                'valid': have_passed_validation and myFactory.boolean(chance_of_getting_true=75),
            }
            new_event = Event(**data)
            if os.path.exists(f'static/medias/event-test-images/{random.randint(1, 9)}.jpg'):
                with open('static/medias/test.png', 'rb') as f:
                    # with ContentFile(f.read()) as f_content:
                    #    new_event.cover_image.save(
                    #        f'file_{myFactory.sentence()[:8]}.jpeg', f_content)

                    lf = tempfile.NamedTemporaryFile(dir='static/medias')
                    lf.write(f.read())
                    # doc object with file FileField.
                    new_event.cover_image.save(
                        f'file_{myFactory.sentence()[:8]}.jpeg', File(lf), save=True)
                    lf.close()

            new_event.save()
            print(new_event)
        except Exception as exc:
            pass
            logger.exception(exc.__str__())


def populate_event_ticket_category_model():
    for event in Event.objects.filter(is_tickets_management_enabled=True, have_passed_validation=True, valid=True):
        if myFactory.boolean(chance_of_getting_true=50):
            for _ in range(random.randint(3, 4)):
                try:
                    data = {
                        'name': myFactory.sentence()[:random.randint(8, 20)],
                        'description': myFactory.text()[:random.randint(70, 300)],
                        'event': event,
                        'organization': event.organization,
                    }
                    new_ticket_category = TicketCategory(**data)
                    new_ticket_category.save()
                    print(new_ticket_category)
                except Exception as exc:
                    pass
                    logger.exception(exc.__str__())


def populate_event_ticket_model():
    tickets = []
    for event in Event.objects.filter(is_tickets_management_enabled=True, have_passed_validation=True, valid=True):
        event_ticket_categories = event.ticket_categories.all()
        if event_ticket_categories.count() > 0:
            for category in event_ticket_categories:
                for _ in range(random.randint(2, 4)):
                    data = {
                        'name': myFactory.sentence()[:random.randint(10, 25)],
                        'description': myFactory.text()[:random.randint(25, 65)],
                        'event': event,
                        'price': myFactory.pyint(min_value=1000, max_value=100000),
                        'available_quantity': myFactory.pyint(min_value=random.randint(7, 99), max_value=1000),
                        'organization': event.organization,
                        "category": category
                    }
                    tickets.append(Ticket(**data))
        else:
            for _ in range(random.randint(2, 4)):
                data = {
                    'name': myFactory.sentence()[:random.randint(10, 25)],
                    'description': myFactory.text()[:random.randint(25, 65)],
                    'event': event,
                    'price': myFactory.pyint(min_value=1000, max_value=100000),
                    'available_quantity': myFactory.pyint(min_value=random.randint(7, 99), max_value=1000),
                    'organization': event.organization
                }
                tickets.append(Ticket(**data))

    try:
        created = Ticket.objects.bulk_create(tickets)
    except Exception as exc:
        pass
        logger.exception(exc.__str__())
