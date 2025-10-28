# -*- coding: utf-8 -*-
"""
Created on September 20 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import transaction
from django.db.models import IntegerField
from django.db.models.functions import Cast

import apps.notifications.tasks as notification_tasks
from apps.events.models import ETicket, Order
from apps.utils.models import Variable
from apps.xlib.enums import OrderStatusEnum, VARIABLE_NAMES_ENUM

logger = get_task_logger(__name__)


@shared_task()
def generate_etickets_for_order(order_id):
    logger.warning(f'\n Begin E-Ticket Generation For Order {order_id} \n')
    order = Order.objects.select_related("item", "item__ticket", "item__ticket__event").get(pk=order_id)

    var = Variable.objects.get(
        name=VARIABLE_NAMES_ENUM.TICKET_NEARLY_SOLD_OUT_PERCENTAGES_FOR_NOTIFICATIONS.value
    )

    var_values = list(
        var.possible_values.annotate(value_as_int=Cast("value", IntegerField())).order_by("value_as_int").values_list(
            "value_as_int", flat=True))

    notifications = []
    # Process Ticket Generation
    logger.info(var_values)
    with transaction.atomic():
        try:
            order.distribute_the_income()
        except Exception as exc:
            raise exc
        order_item = order.item
        event = order_item.ticket.event
        ticket = order_item.ticket

        # Thresholds of tickets for notifications
        _thresholds = [
            {
                "percentage": elmt,
                "test_value": int(ticket.initial_quantity * elmt) / 100
            }
            for elmt in var_values
        ]
        for time in range(int(order_item.quantity)):
            payload = {
                'event': event,
                'ticket': ticket,
                'related_order_id': order.pk,
                'expiration_date': ticket.expiry_date
            }
            e_ticket = ETicket(**payload)
            e_ticket.save()
            e_ticket.generate_qr_code()
            logger.warning(f'Finished Generation of E-Ticket {e_ticket.name}')

        # Todo try to raise an error when tickets not available
        if ticket.available_quantity > 0:
            ticket.available_quantity -= int(order_item.quantity)
        ticket.save(update_fields=['available_quantity'])

        event.participant_count += int(order_item.quantity)
        event.save(update_fields=['participant_count'])
        if ticket.initial_quantity != -1:
            for elmt in _thresholds:
                logger.info(_thresholds)
                logger.info(
                    f"{ticket.available_quantity} < {elmt['test_value']} < {ticket.available_quantity + int(order_item.quantity)}")
                # Check if it is the first time that the available quantity come under the threshold
                if ticket.available_quantity <= elmt['test_value'] < ticket.available_quantity + int(
                        order_item.quantity):
                    notification_tasks.notify_users_about_nearly_sold_out_of_ticket_event.delay(
                        str(event.pk),
                        ticket.name,
                        elmt['percentage'],
                        ticket.available_quantity
                    )

        order.status = OrderStatusEnum.FINISHED.value
        order.save(update_fields=['status'])

    # Process To Notifications

    logger.warning(f'\n End E-Ticket Generation For Order {order_id} \n')

# payload = {'event': event, 'related_order_id': 1, 'expiration_date': datetime.combine(event.date, event.hour)}
