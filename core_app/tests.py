from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from .models import User, PhoneOTP

class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_flow(self):
        # 1. Register
        response = self.client.post('/api/register/', {
            "phone": "+918888888888",
            "name": "Test User",
            "is_photo_public": True
        }, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('otp_code', response.data)
        
        otp = response.data['otp_code']
        
        # 2. Verify Hook (Simulate SMS received)
        verify_response = self.client.post('/api/verify-sms/', {
            "sender_phone": "+918888888888",
            "message_body": otp
        }, format='json')
        
        self.assertEqual(verify_response.status_code, 200)
        
        # 3. Check Status
        user = User.objects.get(phone="+918888888888")
        self.assertTrue(user.is_phone_verified)
        
    def test_peers_privacy_masking(self):
        # Create Online User A (Public Photo)
        User.objects.create(
            phone="+911111111111", name="Alice", 
            is_photo_public=True, photo="http://alice.jpg",
            last_seen=timezone.now()
        )
        # Create Online User B (Private Photo)
        User.objects.create(
            phone="+912222222222", name="Bob", 
            is_photo_public=False, photo="http://bob.jpg",
            last_seen=timezone.now()
        )
        
        response = self.client.get('/api/peers/')
        data = response.data
        
        # Alice should have photo
        alice = next(u for u in data if u['name'] == 'Alice')
        self.assertEqual(alice['photo_url'], "http://alice.jpg")
        
        # Bob should NOT have photo
        bob = next(u for u in data if u['name'] == 'Bob')
        self.assertIsNone(bob['photo_url'])
        
        # Ensure Phone/Email NOT returned
        self.assertNotIn('phone', alice)
        self.assertNotIn('email', alice)

from django.utils import timezone
import datetime
