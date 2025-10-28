# -*- coding: utf-8 -*-
"""
Created on April 28, 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

from apps.notifications.models import NotificationType
from apps.xlib.enums import NOTIFICATION_TYPES_ENUM

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


def populate_notification_type_model():
    for notification_type_tuple in NOTIFICATION_TYPES_ENUM.items():
        try:
            # if notification_type_tuple[0] == NotificationType.ABOUT_FAVOURITE_EVENT:
            #     event_approach_notification_moments_variable = Variable.objects.get(
            #         name=VARIABLE_NAMES_ENUM.EVENT_APPROACH_NOTIFICATIONS_MOMENTS.value)
            #     # event_approach_notification_moments_variable_values_as_list  ====== eanmvval
            #     eanmvval = list(event_approach_notification_moments_variable.possible_values.annotate(value_as_int=Cast(
            #         'value', IntegerField())).order_by('value_as_int').values_list('value_as_int', flat=True))
            #     replacers = {'day': 'Jour', 'days': 'Jours', 'month': 'Mois', 'months': 'Mois', 'year': 'Année',
            #                  'years': 'Années'}
            #     for value in eanmvval:
            #         NotificationType.objects.create(name=notification_type_tuple[0],
            #                                         description=f'{replace_english_words(replacers, timedelta(seconds=value).__str__())}')
            # else:
            NotificationType.objects.get_or_create(name=notification_type_tuple[0],
                                                   defaults={"description": notification_type_tuple[0]})
        except Exception as exc:
            logger.exception(exc.__str__())
