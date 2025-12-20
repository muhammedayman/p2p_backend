import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import ProfileUser
import datetime
import logging
from .utils import get_client_ip_from_scope

logger = logging.getLogger(__name__)

class SignalingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # user_id is passed in the URL route: ws/signal/<user_id>/
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f'user_{self.user_id}'
        self.ip = get_client_ip_from_scope(self.scope)

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
            
            # --- Network Topology & Logging ---
            if target_phone:
                target_ip = await self.get_user_ip(target_phone)
                network_status = "[DIFFERENT NETWORK]"
                is_same_network = False
                if self.ip and target_ip and self.ip == target_ip:
                    network_status = "[SAME NETWORK]"
                    is_same_network = True
                
                logger.info(f"Signaling Message: Type={type}, Sender={self.user_id} ({self.ip}) -> Target={target_phone} ({target_ip}) {network_status}")
            else:
                 logger.warning(f"Signaling failed: Target {target_id} not found. Sender={self.user_id}")
                 is_same_network = False

            if target_phone:
                # Forward message to target user
                await self.channel_layer.group_send(
                    f'user_{target_phone}',
                    {
                        'type': 'signaling_message',
                        'sender': self.user_id,
                        'msg_type': type,
                        'payload': payload,
                        'is_same_network': is_same_network
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

    @database_sync_to_async
    def get_user_ip(self, phone):
        try:
             return ProfileUser.objects.get(phone=phone).ip
        except ProfileUser.DoesNotExist:
             return None

    # Receive message from room group
    async def signaling_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'sender': event['sender'],
            'type': event['msg_type'],
            'payload': event['payload'],
            'is_same_network': event.get('is_same_network', False)
        }))
