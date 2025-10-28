# -*- coding: utf-8 -*-
"""
Created on April 28 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging

import requests
from django.conf import settings
from dotenv import load_dotenv, find_dotenv

headers = {
    'Content-Type': 'application/json',
}

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)
logger.setLevel('INFO')

api_key = settings.MJ_APIKEY_PUBLIC
api_secret = settings.MJ_APIKEY_PRIVATE


def send(params: dict, variables: dict) -> dict:
    email = params['email']
    full_name = params['full_name']
    template_id = params['template_id']

    json_data = {
        'Messages': [
            {
                'From': {
                    'Email': 'wuloevents@gmail.com',
                    'Name': 'Wulo Events',
                },
                'To': [
                    {
                        'Email': email,
                        'Name': full_name,
                    },
                ],
                'TemplateID': template_id,
                'TemplateLanguage': True,
                'Variables': variables
            },
        ],
    }
    try:
        response = requests.post(
            'https://api.mailjet.com/v3.1/send',
            headers=headers,
            json=json_data,
            auth=(api_key, api_secret),
        )
        if not str(response.status_code) == '200':
            raise ValueError({'data': response.json()})
    except Exception as exc:
        logger.exception(exc.__str__())
