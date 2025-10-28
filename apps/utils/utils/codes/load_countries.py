# -*- coding: utf-8 -*-
"""
Created on April 26 2022

@author:
    Wesley Eliel MONTCHO
"""

import json

import requests


def format_data(unordered_data):
    data = []

    for item in unordered_data:
        data.append(
            {
                "name": {
                    "fr": item['translations']['fr'],
                    "en": item['name']
                },
                "flag": item['flags']['svg'],
                "code": item['alpha2Code'],
                "prefix": item['callingCodes'][0],
                "region": item['region'],
                "subregion": item['subregion']
            }
        )
    return data


response = requests.get(
    "https://restcountries.com/v2/all/?fields=name,alpha2Code,callingCodes,translations,flags,region,subregion")

formatted_data = format_data(response.json())

with open('../files/countries.json', 'w', encoding='utf-8') as f:
    json.dump(formatted_data, f, ensure_ascii=False, indent=4)
