# -*- coding: utf-8 -*-
"""
Created on June 15 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

import json
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.users.models import Transaction
from apps.utils.models import CeleryTask

logger = logging.getLogger(__name__)
logger.setLevel('INFO')


class TransactionsConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['transaction_local_id']
        self.room_group_name = 'room_%s' % self.room_name

        logger.warning(self.room_name)
        logger.warning("\n Try to connect to websocket room {} \n".format(self.room_name))
        try:
            payment = Transaction.objects.get(local_id=self.room_name)
            payment_tasks = payment.tasks.filter(type=CeleryTask.PAYMENT_TRANSACTION_CALLBACK,
                                                 status=CeleryTask.TASK_STATUS_PENDING)
            if not payment_tasks.exists():
                logger.warning(
                    "There is no payment in progress for the transaction {}".format(self.room_name))
                await self.close(code="There is not payment in process for this transaction.")
            else:
                # Join room group
                await self.channel_layer.group_add(
                    self.room_group_name,
                    self.channel_name
                )
                await self.accept()

                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'send_message',
                    'message': "Hello",
                    'event': "CONNECTED"
                })
            logger.warning("\n Connected to websocket room {} \n".format(self.room_name))

        except Exception as exc:
            logger.warning(exc.__str__())
            await self.close(code="Some error occur")

    async def disconnect(self, close_code):
        logger.debug("Disconnected")
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Receive message from WebSocket.
        Get the event and send the appropriate event
        """
        logger.debug(text_data)
        response = json.loads(text_data)
        try:
            event = response.get("event", None)
            message = response.get("message", None)

            if event == 'TRANSACTION_END':
                # Send message to room group
                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'send_message',
                    'message': message,
                    'event': "TRANSACTION_END"
                })
        except Exception as exc:
            logger.debug(exc.__str__())
            logger.log(exc.__str__())
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'send_message',
                'message': response,
            })

    async def send_message(self, res):
        """ Receive message from room group """
        # Send message to WebSocket
        await self.send(text_data=json.dumps(res))
        if res['event'] == "TRANSACTION_END":
            await self.disconnect(close_code="")
