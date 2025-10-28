# -*- coding: utf-8 -*-
"""
Created on 18/09/2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""
from decimal import Decimal
from typing import List

from apps.events.models import Event, Order, ETicket
from apps.events.serializers import LightTicketSerializer
from apps.organizations.models import Organization
from apps.users.serializers import UserSerializerLight
from apps.xlib.enums import OrderStatusEnum


def generate_stats_for_events(organization: Organization, events: List[Event]) -> list:
    data = []

    for event in events:
        ticket_data = []
        for ticket in event.tickets.all():
            # Todo: Add discount usages to stats data
            quantity_sold = 0
            entries = Decimal("0")
            amount_earn = Decimal("0")
            related_orders = Order.objects.select_related('item').only("applied_percentage", "item").filter(
                item__ticket_id=ticket.pk, status=OrderStatusEnum.FINISHED.value)
            for order in related_orders:
                potential_discount_data = order.item.potential_discount_data
                _entry = order.item.line_total if not potential_discount_data.get("use_coupon", False) else Decimal(
                    potential_discount_data.get("reduced_amount"))
                _amount_earn = Decimal(1 - order.applied_percentage) * _entry

                quantity_sold += order.item.quantity
                entries += _entry
                amount_earn += _amount_earn

                # entries = ticket.price * Decimal(e_tickets_length)
            _data = {
                "name": ticket.name,
                "available_quantity": ticket.available_quantity,
                "sold": quantity_sold,
                "entries": entries,
                "amount_earn": amount_earn

            }
            ticket_data.append(_data)

        data.append({
            "id": str(event.pk),
            "name": event.name,
            "views": event.views,
            "participant_count": event.participant_count,
            "percentage_for_wuloevents": organization.get_retribution_percentage(),
            "tickets_data": ticket_data,
            "total_earn": sum([elmt["amount_earn"] for elmt in ticket_data])
        })
    return data


def get_event_participants(event_pk: str, users_ids: list = []):
    def update_or_create_count_for_ticket_for_user(_dictionary, _ticket):
        key = str(_ticket.pk)
        if key in _dictionary:
            _dictionary[key]['count'] += 1
        else:
            _dictionary[key] = {**LightTicketSerializer(ticket).data, 'count': 1}
        return _dictionary

    e_tickets = ETicket.objects.select_related("related_order__user", "ticket").filter(
        event_id=event_pk, related_order__user_id__in=users_ids)

    infos = {}

    for index, e_ticket in enumerate(e_tickets):
        related_user = e_ticket.related_order.user
        user_pk = str(related_user.pk)
        ticket = e_ticket.ticket
        if user_pk not in infos:
            infos[user_pk] = UserSerializerLight(related_user).data

        tickets = infos[user_pk].get("tickets", {})

        infos[user_pk]["tickets"] = update_or_create_count_for_ticket_for_user(tickets, ticket)

    return [{**item, "tickets": list(item['tickets'].values())} for item in infos.values()]
