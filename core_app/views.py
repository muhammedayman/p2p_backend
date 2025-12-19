from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import ProfileUser, PhoneOTP, EmailOTP
from .serializers import UserRegistrationSerializer, PeerSerializer
import random
import datetime


# --- AUTHENTICATION ---

class RegisterView(APIView):
    def post(self, request):
        """
        Register/Update User.
        Returns 'phone_otp_code' which user must SMS to +917012710457.
        """
        data = request.data
        phone = data.get('phone')
        
        # Upsert User
        user, created = ProfileUser.objects.update_or_create(
            phone=phone,
            defaults={
                'name': data.get('name'),
                'email': data.get('email'),
                'photo': data.get('photo'),
                'is_photo_public': data.get('is_photo_public', False),
                'last_seen': timezone.now()
            }
        )
        
        # Generate Phone OTP (Code to be sent via SMS)
        code = str(random.randint(1000, 9999))
        PhoneOTP.objects.create(phone=phone, otp_code=code)
        
        return Response({
            "status": "pending_verification",
            "message": f"Please send SMS '{code}' to +917012710457",
            "otp_code": code,
            "target_number": "+917012710457"
        })

class VerifySMSWebhookView(APIView):
    """
    Called by the Admin/SMS-Gateway app when an SMS is received.
    """
    def post(self, request):
        sender = request.data.get('sender_phone') # e.g., +919876543210
        msg_body = request.data.get('message_body', '').strip()
        
        # Find pending OTP request
        # We look for an OTP record where the code matches the message body
        # and the phone matches (or near match)
        
        try:
            # Simple exact match for demo
            otp_record = PhoneOTP.objects.filter(
                otp_code=msg_body,
                created_at__gte=timezone.now() - datetime.timedelta(minutes=10)
            ).last()  # Get latest
            
            if otp_record and (sender in otp_record.phone or otp_record.phone in sender):
                # Mark User Verified
                ProfileUser.objects.filter(phone=otp_record.phone).update(is_phone_verified=True)
                return Response({"status": "verified", "phone": otp_record.phone})
            
            return Response({"status": "failed", "reason": "No matching OTP found"}, status=400)
            
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class EmailOTPRequestView(APIView):
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email required"}, status=400)
            
        code = str(random.randint(100000, 999999))
        EmailOTP.objects.create(email=email, otp_code=code)
        
        # In production, send via SMTP. Here: Print to console.
        print(f"=====================================")
        print(f" [MOCK EMAIL] To: {email} | Code: {code}")
        print(f"=====================================")
        
        return Response({"message": "OTP sent to email (check console)"})

class EmailOTPVerifyView(APIView):
    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('otp')
        
        valid = EmailOTP.objects.filter(
            email=email, 
            otp_code=code,
            created_at__gte=timezone.now() - datetime.timedelta(minutes=10)
        ).exists()
        
        if valid:
            ProfileUser.objects.filter(email=email).update(is_email_verified=True)
            return Response({"status": "verified"})
        return Response({"status": "invalid"}, status=400)

class UserStatusView(APIView):
    def get(self, request):
        phone = request.query_params.get('phone')
        user = ProfileUser.objects.filter(phone=phone).first()
        if user:
            return Response({
                "is_phone_verified": user.is_phone_verified,
                "is_email_verified": user.is_email_verified
            })
        return Response({"error": "User not found"}, status=404)

# --- SIGNALING & DISCOVERY ---

class HeartbeatView(APIView):
    def post(self, request):
        phone = request.data.get('phone')
        ip = request.data.get('ip')
        port = request.data.get('port')
        
        ProfileUser.objects.filter(phone=phone).update(
            ip=ip, 
            port=port, 
            last_seen=timezone.now()
        )
        return Response({"status": "updated"})

class PeersListView(APIView):
    def get(self, request):
        # Filter: Online (last 2 mins)
        cutoff = timezone.now() - datetime.timedelta(minutes=2)
        
        # Exclude self (optional, if phone param passed)
        my_phone = request.query_params.get('phone')
        
        queryset = ProfileUser.objects.filter(last_seen__gt=cutoff)
        if my_phone:
            queryset = queryset.exclude(phone=my_phone)
            
        # Serialize (Handles masking of phone/email)
        serializer = PeerSerializer(queryset, many=True)
        return Response(serializer.data)

class TURNCredentialsView(APIView):
    def get(self, request):
        # Return ephemeral credentials for Coturn
        # In reality, generate these using the TURN shared secret
        return Response({
            "username": "user",
            "password": "password",
            "uris": ["turn:your-turn-server-ip:3478"]
        })
