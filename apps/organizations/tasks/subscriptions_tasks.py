# -*- coding: utf-8 -*-
"""
Created on December 12 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from celery import shared_task
from celery.utils.log import get_task_logger

from apps.organizations.models import Subscription

logger = get_task_logger(__name__)


@shared_task()
def update_subscriptions_active_status():
    logger.info('\n Begin Update Subscription Status Task \n')
    try:
        subscription = Subscription.objects.update_status()
        logger.info(subscription)
    except Exception as exc:
        logger.exception(exc.__str__())
    logger.info('\n Finish Update Subscription Status Task \n')
    # TODO Add Model Fo Storing Celery Tasks
