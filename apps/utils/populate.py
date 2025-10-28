# -*- coding: utf-8 -*-
"""
Created on April 28 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import json

from apps.utils.models import Country, Variable, VariableValue
# COUNTRY_CHOICES = ["226", "257", "229", "237", "242", "243", "225", "253", "241" "224", "240", "261" ,"223", "227",
# "250", "236", "248", "221", "235", "228" ]
from apps.xlib.enums import VARIABLE_NAMES_ENUM

COUNTRY_CHOICES = ["229", "228"]
country_json = json.load(open('apps/utils/utils/files/countries.json', encoding='utf-8'), )


def populate_country():
    for country in country_json:
        data = {
            'name': country['name']['fr'],
            'code': country['code'],
            'prefix': country['prefix'],
            'is_covered': country['prefix'] in COUNTRY_CHOICES,
        }
        Country.objects.get_or_create(name=data["name"], defaults=data)


def populate_variables():
    ################
    label = "ADRESSE DE BASE ACTUELLE DU SITE"
    site_variable, sv_created = Variable.objects.get_or_create(name=VARIABLE_NAMES_ENUM.CURRENT_SITE_BASE_ADDRESS.value,
                                                               defaults={"type": 'str', "is_unique": True,
                                                                         "label": label})
    if sv_created:
        VariableValue.objects.create(variable=site_variable, value="https://api.wuloevents.com")

    ################
    label = "POURCENTAGE SUR LA VENTE D'UN BILLET"
    percentage_variable, pv_created = Variable.objects.get_or_create(
        name=VARIABLE_NAMES_ENUM.PERCENTAGE_ABOUT_A_TICKET_SELLING.value,
        defaults={"type": 'float', "is_unique": True, "label": label}
    )
    if pv_created:
        VariableValue.objects.create(variable=percentage_variable, value="0.05")

    ################
    label = "POURCENTAGE SUR LA VENTE D'UN BILLET AVEC RÉDUCTION"
    percentage_with_discount_variable, pwdv_created = Variable.objects.get_or_create(
        name=VARIABLE_NAMES_ENUM.PERCENTAGE_ABOUT_A_TICKET_SELLING_WITH_DISCOUNT.value,
        defaults={"type": 'float', "is_unique": True, "label": label}
    )
    if pwdv_created:
        VariableValue.objects.create(variable=percentage_with_discount_variable, value="0.05")

    ################
    label = "MONTANT MINIMAL REQUIS POUR UN RETRAIT"
    minimal_amount_for_withdraw_variable, mafwv_created = Variable.objects.get_or_create(
        name=VARIABLE_NAMES_ENUM.MINIMAL_AMOUNT_REQUIRED_FOR_WITHDRAW.value,
        defaults={"type": 'float', "is_unique": True, "label": label}
    )
    if mafwv_created:
        VariableValue.objects.create(variable=minimal_amount_for_withdraw_variable, value="10000.00")

    #############
    label = "MONTANT MINIMAL REQUIS POUR COUVRIR LE COÛT DES RETRAITS"
    minimal_amount_to_cover_withdrawal_cost, matcwc_created = Variable.objects.get_or_create(
        name=VARIABLE_NAMES_ENUM.MINIMAL_AMOUNT_REQUIRED_TO_COVER_WITHDRAWALS_COST.value,
        defaults={"type": 'float', "is_unique": True, "label": label}
    )
    if matcwc_created:
        VariableValue.objects.create(variable=minimal_amount_to_cover_withdrawal_cost, value="50000.00")

    ################
    label = "MOMENTS DE NOTIFICATIONS DE L'APPROCHE D 'ÉVÉNEMENTS FAVORIS"
    event_approach_notifications_moments_variable, eanmv_created = Variable.objects.get_or_create(
        name=VARIABLE_NAMES_ENUM.EVENT_APPROACH_NOTIFICATIONS_MOMENTS.value,
        defaults={"type": "int", "is_unique": False, "label": label})

    if eanmv_created:
        moments_in_minutes = [3600, 86400, 259200]
        VariableValue.objects.bulk_create(
            [VariableValue(variable=event_approach_notifications_moments_variable, value=value) for value in
             moments_in_minutes])

    ################
    label = "POURCENTAGES POUR LES NOTIFICATIONS DE BILLETS PRESQUE ÉPUISÉS"
    ticket_nearly_sold_out_notifications_moment_variable, tnsonmv_created = Variable.objects.get_or_create(
        name=VARIABLE_NAMES_ENUM.TICKET_NEARLY_SOLD_OUT_PERCENTAGES_FOR_NOTIFICATIONS.value,
        defaults={"type": "int", "is_unique": False, "label": label}
    )

    if tnsonmv_created:
        percentages = [20, 10]
        VariableValue.objects.bulk_create(
            [
                VariableValue(variable=ticket_nearly_sold_out_notifications_moment_variable, value=value) for value in
                percentages
            ]
        )


"""exec(open('apps/utils/populate.py').read())"""
"""admin@wuloevent.com, admin"""
