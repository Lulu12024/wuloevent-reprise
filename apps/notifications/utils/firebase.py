# -*- coding: utf-8 -*-
"""
Created on August 20 2024

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import requests
from django.conf import settings

from helpers.singleton import Singleton


class FirebaseDynamicLinkGenerator(metaclass=Singleton):
    FIREBASE_API_URL = 'https://firebasedynamiclinks.googleapis.com/v1/shortLinks?key={}'

    def __init__(self):
        self.api_url = self.FIREBASE_API_URL.format(settings.FIREBASE_APP_WEB_API_KEY)

    def generate(self, link, short=False, meta_tag_info={}):
        payload = {
            "dynamicLinkInfo": {
                "domainUriPrefix": settings.FIREBASE_APP_DOMAINE,
                "link": link,
                "androidInfo": {
                    "androidPackageName": "com.wuloevents.clients"
                },
                "iosInfo": {
                    "iosBundleId": "com.wuloevents.clients"
                },
                "socialMetaTagInfo": meta_tag_info
                # {
                #     "socialTitle": string,
                #     "socialDescription": string,
                #     "socialImageLink": string
                # }

            },
            "suffix": {
                "option": "SHORT" if short else "UNGUESSABLE"
            }
        }

        ## request firebase dynamic link
        response = requests.post(self.api_url, json=payload)

        data = response.json()

        ## return response if not success
        if not response.status_code == 200:
            return data

        ## return link data if success response
        return data['shortLink']
