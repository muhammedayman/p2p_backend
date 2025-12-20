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
        logger.info(f"============================================")
        logger.info(f"[WEBSOCKET] CONNECTION ATTEMPT")
        logger.info(f"[WEBSOCKET] User={self.user_id}")
        logger.info(f"[WEBSOCKET] Scope path: {self.scope.get('path')}")
        logger.info(f"============================================")
        
        self.ip = get_client_ip_from_scope(self.scope)
        logger.info(f"[WEBSOCKET] IP detected: {self.ip}")

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.update_user_status(online=True, ip=self.ip)
        await self.accept()
        
        logger.info(f"[WEBSOCKET] ✓ CONNECTION ACCEPTED for user {self.user_id}")
        
        # Send Version/Debug Info on Connect
        await self.send(text_data=json.dumps({
            "type": "welcome",
            "version": "SERVER_FIXED_V2",
            "ip_detected": self.ip,
            "channel_name": self.channel_name
        }))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        await self.update_user_status(online=False)

    @database_sync_to_async
    def update_user_status(self, online=True, ip=None):
        if online:
            update_fields = {'last_seen': timezone.now()}
            if ip:
                update_fields['ip'] = ip
            ProfileUser.objects.filter(phone=self.user_id).update(**update_fields)
        else:
            # Set to past to remove from online list immediately
            past = timezone.now() - datetime.timedelta(minutes=10)
            ProfileUser.objects.filter(phone=self.user_id).update(last_seen=past)

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            logger.info(f"[RECEIVE] Method called - raw text_data type: {type(text_data)}")
            logger.info(f"[RECEIVE] Raw text_data: {text_data[:200] if isinstance(text_data, str) else text_data}")
            
            data = json.loads(text_data)
            logger.info(f"[RECEIVE] JSON parsed successfully: {data}")
            
            target_id = data.get('target')
            payload = data.get('payload') 
            msg_type = data.get('type') # 'offer', 'answer', 'ice-candidate'
            
            logger.info(f"[RECEIVE] received target_id={target_id} payload={str(payload)[:100] if payload else None}")

            if target_id:
                # Resolve target ID to Phone Number (Group Name)
                target_phone = await self.get_target_phone(target_id)
                
                # --- Network Topology & Logging ---
                if target_phone:
                    target_ip = await self.get_user_ip(target_phone)
                    network_status = "[DIFFERENT NETWORK]"
                    is_same_network = False
                    
                    # Robust Network Check (Handles IPv6 Subnets)
                    if self.is_same_network_check(self.ip, target_ip):
                        network_status = "[SAME NETWORK]"
                        is_same_network = True
                    
                    logger.info(f"Signaling Message: Type={msg_type}, Sender={self.user_id} ({self.ip}) -> Target={target_phone} ({target_ip}) {network_status}")
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
                            'msg_type': msg_type,
                            'payload': payload,
                            'is_same_network': is_same_network,
                            'debug_sender_ip': self.ip,
                            'debug_target_ip': target_ip
                        }
                    )
            else:
                logger.warning(f"[RECEIVE] No target_id in message. Message data: {data}")
                
        except json.JSONDecodeError as e:
            logger.error(f"[RECEIVE] JSON Decode Error: {str(e)} - Raw data: {text_data[:200]}")
        except Exception as e:
            logger.error(f"[RECEIVE] Unexpected error: {type(e).__name__}: {str(e)}", exc_info=True)
    
    @database_sync_to_async
    def get_target_phone(self, target_id):
        try:
            # 1. Try to find user by ID first (if it looks like an ID)
            if str(target_id).isdigit():
                try:
                    user = ProfileUser.objects.get(id=int(target_id))
                    return user.phone
                except ProfileUser.DoesNotExist:
                    pass

            # 2. Check if target_id is already a phone (legacy or direct)
            if target_id.startswith('+') or target_id.isdigit():
                 return target_id
                 
            # 3. Fallback: Assume it might be a specific database ID (string format?)
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
            'is_same_network': event.get('is_same_network', False),
            'debug_ips': f"SenderIP={event.get('debug_sender_ip')} TargetIP={event.get('debug_target_ip')}"
        }))

    def is_same_network_check(self, ip1, ip2):
        if not ip1 or not ip2:
            return False
            
        # Exact Match (IPv4 or Identical IPv6)
        if ip1 == ip2:
            return True
            
        # IPv6 Subnet Match (/64)
        if ':' in ip1 and ':' in ip2:
            try:
                # 2409:4900:8fdc:bb70:78a0:6ff:fef1:4a89
                # Compare first 4 blocks (64 bits)
                parts1 = ip1.split(':')
                parts2 = ip2.split(':')
                if len(parts1) >= 4 and len(parts2) >= 4:
                    prefix1 = parts1[:4]
                    prefix2 = parts2[:4]
                    return prefix1 == prefix2
            except Exception:
                pass
                
        return False
