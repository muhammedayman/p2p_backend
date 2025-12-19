from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import ProfileUser, PhoneOTP, EmailOTP, AuthenticationCode
from .serializers import UserRegistrationSerializer, PeerSerializer
import random
import datetime


# --- AUTHENTICATION ---

class RegisterView(APIView):
    def post(self, request):
        """
        Register/Update User.
        Returns 'phone_otp_code' which user must SMS to +917012710457.
        Also generates and returns a unique 'secret_code' for app-based auto-login.
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
        phoneotp_obj, created = PhoneOTP.objects.update_or_create(phone=phone,user=user)
        phoneotp_obj.otp_code = code
        phoneotp_obj.save()
        
        # Generate Authentication Code for app-based login
        secret_code = AuthenticationCode.generate_code()
        auth_code_obj, _ = AuthenticationCode.objects.update_or_create(
            user=user,
            defaults={
                'secret_code': secret_code,
                'user_data': {
                    'name': data.get('name'),
                    'phone': phone,
                    'email': data.get('email')
                },
                'is_active': True
            }
        )
        
        return Response({
            "status": "pending_verification",
            "message": f"Please send SMS '{code}' to +917012710457",
            "otp_code": code,
            "target_number": "+917012710457",
            "secret_code": secret_code,
            "secret_code_message": "Save this code in your app for automatic login next time"
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

class LoginWithSecretCodeView(APIView):
    """
    Auto-login endpoint for users with saved secret code.
    Used when app has previously registered and saved the secret_code.
    """
    def post(self, request):
        """
        Expects: {
            "secret_code": "<the saved secret code>"
        }
        
        Returns: User details and verification status
        """
        secret_code = request.data.get('secret_code')
        
        if not secret_code:
            return Response(
                {"error": "secret_code is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Find the auth code record
            auth_code = AuthenticationCode.objects.select_related('user').get(
                secret_code=secret_code,
                is_active=True
            )
            
            user = auth_code.user
            
            # Update last_seen
            user.last_seen = timezone.now()
            user.save(update_fields=['last_seen'])
            
            # Update last_used timestamp
            auth_code.last_used = timezone.now()
            auth_code.save(update_fields=['last_used'])
            
            # Return user info and verification status
            return Response({
                "status": "success",
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "phone": user.phone,
                    "email": user.email,
                    "photo": user.photo,
                    "is_photo_public": user.is_photo_public,
                    "is_phone_verified": user.is_phone_verified,
                    "is_email_verified": user.is_email_verified,
                    "is_online": user.is_online()
                },
                "message": f"Welcome back, {user.name}!"
            }, status=status.HTTP_200_OK)
            
        except AuthenticationCode.DoesNotExist:
            return Response(
                {"error": "Invalid or inactive secret code"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VerifySecretCodeView(APIView):
    """
    Endpoint to check if a secret code is valid without logging in.
    Useful for checking code validity before attempting auto-login.
    """
    def get(self, request):
        """
        Expects: ?secret_code=<code>
        """
        secret_code = request.query_params.get('secret_code')
        
        if not secret_code:
            return Response(
                {"error": "secret_code is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        exists = AuthenticationCode.objects.filter(
            secret_code=secret_code,
            is_active=True
        ).exists()
        
        return Response({
            "is_valid": exists,
            "secret_code": secret_code if exists else None
        })
