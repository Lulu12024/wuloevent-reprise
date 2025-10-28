# -*- coding: utf-8 -*-
"""
Created on July 14, 2023

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import logging
import string
from datetime import datetime
from decimal import Decimal

from django.db import models
from django.utils.crypto import get_random_string
from model_utils import FieldTracker

from apps.users.models import Transaction
from apps.users.models.utils import get_transaction_default_coupon_metadata
from apps.utils.validators import PhoneNumberValidator
from apps.xlib.enums import OrderStatusEnum, TransactionKindEnum
from commons.models import AbstractCommonBaseModel

logger = logging.getLogger(__name__)
logger.setLevel('INFO')

SEX_CHOICES = (
    ("F", "Féminin"),
    ("M", "Masculin"),
    ("A", "Autres"),
)


class OrderItem(AbstractCommonBaseModel):
    ticket = models.ForeignKey(to="events.Ticket", verbose_name='Ticket',
                               related_name='ordered_items', on_delete=models.DO_NOTHING)
    quantity = models.IntegerField(default=1)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    potential_discount_data = models.JSONField(verbose_name="Information d' une potentielle réduction",
                                               default=get_transaction_default_coupon_metadata)

    class Meta:
        verbose_name = "Item d' une commande"
        verbose_name_plural = "Items de commandes"

    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.ticket.price
        return super().save(*args, **kwargs)


class Order(AbstractCommonBaseModel):
    user = models.ForeignKey(
        "users.User", blank=True, null=True, on_delete=models.SET_NULL, related_name="related_orders")

    item = models.OneToOneField(OrderItem, on_delete=models.DO_NOTHING, verbose_name="Item de la commande", null=True,
                                related_name="order")
    name = models.CharField(verbose_name='Nom Complet',
                            max_length=30, blank=True)
    # Important: Email address now used for anonymous purchases
    email = models.EmailField(
        verbose_name='Adresse mail', blank=True, null=True)
    sex = models.CharField(verbose_name='Sexe', max_length=10,
                           choices=SEX_CHOICES, blank=True, null=True)
    phone = models.CharField(verbose_name='Numéro de téléphone', max_length=25, blank=True,
                             null=True, validators=[PhoneNumberValidator()])
    order_id = models.CharField(max_length=120, unique=True)
    status = models.CharField(
        max_length=120,

        choices=OrderStatusEnum.items(),
        default=OrderStatusEnum.SUBMITTED.value
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    tracker = FieldTracker()
    applied_percentage = models.FloatField(default=False, verbose_name="Pourcentage appliqué")
    has_been_discounted = models.BooleanField(default=False,
                                              verbose_name="Désigne si la commande est objet d' une réduction.")

    is_income_distributed = models.BooleanField(default=False, verbose_name="Désigne si les revenu ont été distribués")
    # Pseudo anonyme, un cas ou l'utilisateur n' est pas connecté et vient payer en associant juste son mail et
    # attendant que le ticket lui soit envoyé par email
    is_pseudo_anonymous = models.BooleanField(default=False, verbose_name="Désigne l'achat est pseudo anonyme")

    def __str__(self) -> str:
        if self.user and self.user is None:
            return str(self.order_id + ' \t' + self.user.get_full_name())
        else:
            return str(self.order_id + ' \t' + str(self.user))

    @property
    def total(self):
        return self.item.line_total

    @property
    def is_valid(self):
        try:
            related_order_transaction = Transaction.objects.get(type=TransactionKindEnum.ORDER.value, entity_id=self.pk)
            return related_order_transaction.paid
        except:
            return False

    def save(self, *args, **kwargs) -> None:
        if self.order_id == '' or self.order_id is None:
            today = datetime.now().strftime('%Y%m%d')
            self.order_id = f'CMD-{get_random_string(8, allowed_chars=string.digits + string.ascii_uppercase)}'
        return super().save(*args, **kwargs)

    def distribute_the_income(self):
        if not self.is_income_distributed:
            order_item = self.item
            line_total = order_item.line_total
            if self.has_been_discounted:
                line_total = order_item.potential_discount_data.get("reduced_amount", line_total)

            organization = order_item.ticket.event.organization
            to_apply_percentage = organization.get_retribution_percentage(self.has_been_discounted)
            financial_account = organization.get_financial_account
            income = Decimal(
                line_total) * Decimal(1 - to_apply_percentage)
            financial_account.balance += income
            financial_account.save(update_fields=['balance'])

            self.is_income_distributed = True
            self.applied_percentage = to_apply_percentage
            self.save(update_fields=['is_income_distributed', 'applied_percentage'])

    def get_income_distribution_data(self):
        data = {}
        order_item = self.item
        line_total = order_item.line_total
        organization = order_item.ticket.event.organization
        to_apply_percentage = organization.get_retribution_percentage(self.has_been_discounted)

        income = Decimal(
            line_total) * Decimal(1 - to_apply_percentage)

        if organization.pk not in data.keys():
            data[organization.pk] = {'organization': {
                "name": organization.name, "owner_mail": organization.owner.email,
                'owner_full_name': organization.owner.get_full_name()}, 'enum': [], 'income': 0}
        event = order_item.ticket.event
        ticket = order_item.ticket
        quantity = order_item.quantity
        data[organization.pk]['income'] += income
        data[organization.pk]['enum'].append(
            {'event_name': event.name, 'ticket_name': ticket.name, 'quantity': quantity, 'partial_income': income})
        return data

    class Meta:
        verbose_name = "Commande de ticket"
        verbose_name_plural = "Commandes de Tickets"
