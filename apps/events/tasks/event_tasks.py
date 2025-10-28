# -*- coding: utf-8 -*-
"""
Created on July 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

""""@shared_task()
def notify_users_about_the_approach_of_favourite_event():
    event_approach_notification_moments_variable = Variable.objects.get(name=Variable.VARIABLE_NAME_EVENT_APPROACH_NOTIFICATIONS_MOMENTS)
    # Work with aggreation to only get the converted variable
    event_approach_notification_moments_values = []
    logger.info('\n Begin Notifications About Event Task \n')
    for favourite_event in FavouriteEvent.objects.all():
        # Verifier si la date est dans 
        if favourite_event.event.date == '':
            pass

    logger.info('\n Finished Notifications About Event Tas \n')

"""
