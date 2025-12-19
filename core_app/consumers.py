import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import ProfileUser
import datetime

class SignalingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # user_id is passed in the URL route: ws/signal/<user_id>/
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f'user_{self.user_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.update_user_status(online=True)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        await self.update_user_status(online=False)

    @database_sync_to_async
    def update_user_status(self, online=True):
        if online:
            ProfileUser.objects.filter(phone=self.user_id).update(last_seen=timezone.now())
        else:
            # Set to past to remove from online list immediately
            past = timezone.now() - datetime.timedelta(minutes=10)
            ProfileUser.objects.filter(phone=self.user_id).update(last_seen=past)

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        target_id = data.get('target')
        payload = data.get('payload') 
        type = data.get('type') # 'offer', 'answer', 'ice-candidate'

        if target_id:
            # Resolve target ID to Phone Number (Group Name)
            target_phone = await self.get_target_phone(target_id)
            if target_phone:
                # Forward message to target user
                await self.channel_layer.group_send(
                    f'user_{target_phone}',
                    {
                        'type': 'signaling_message',
                        'sender': self.user_id,
                        'msg_type': type,
                        'payload': payload
                    }
                )
    
    @database_sync_to_async
    def get_target_phone(self, target_id):
        try:
            # Check if target_id is already a phone (legacy or direct)
            if target_id.startswith('+') or target_id.isdigit():
                 return target_id
                 
            # Assume it's a Database ID
            user = ProfileUser.objects.get(id=target_id)
            return user.phone
        except (ProfileUser.DoesNotExist, ValueError):
            return None

    # Receive message from room group
    async def signaling_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'sender': event['sender'],
            'type': event['msg_type'],
            'payload': event['payload']
        }))
