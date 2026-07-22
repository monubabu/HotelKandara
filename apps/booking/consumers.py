import json
from channels.generic.websocket import AsyncWebsocketConsumer


class AvailabilityConsumer(AsyncWebsocketConsumer):
      async def connect(self):
            #name of the shared room for room availability
            self.group_name = "room_availability"

            #joining channel groups
            await self.channel_layer.group_add(
                  self.group_name,
                  self.channel_name

            )
            await self.accept()

      async def disconnect(self, close_code):
            #leave the channel grp on disconnect
            await self.channel_layer.group_discard(
                  self.group_name,
                  self.channel_name
            )

      #Handlers method triggers when broadcast is sent to "room availablity"
      async def room_status_update(self, event):
            #send json message directly to connected client
            await self.send(text_dat=json.dumps({
                  'type':'ROOM_STATUS_CHANGED',
                  'room_id': event['room_id'],
                  'room_number': event['room_number'],
                  'new_status': event['new_status'],
                  'message': event['message']
            }))