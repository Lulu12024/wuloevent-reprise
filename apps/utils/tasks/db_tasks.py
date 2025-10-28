# -*- coding: utf-8 -*-
"""
Created on July 26 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command

logger = get_task_logger(__name__)


@shared_task()
def backup_db():
    logger.info('\n Begin BD Backup \n')
    call_command('save_data_as_json')
    logger.info('\n Finished DB Backup \n')
