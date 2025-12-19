from django.db import models
from django.utils import timezone
import datetime
import secrets
import json

class ProfileUser(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, unique=True)
    email = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    # Profile Photo (URL or Base64 string)
    photo = models.TextField(blank=True, null=True)
    is_photo_public = models.BooleanField(default=False)
    
    # Connectivity Info (Ephemeral)
    ip = models.GenericIPAddressField(null=True, blank=True)
    port = models.IntegerField(null=True, blank=True)
    last_seen = models.DateTimeField(auto_now=True)
    
    # Verification Status
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)

    def is_online(self):
        # Online if seen in last 2 minutes
        if not self.last_seen:
            return False
        return timezone.now() - self.last_seen < datetime.timedelta(minutes=2)

    def __str__(self):
        return f"{self.name} ({self.phone})"

    class Meta:
        db_table = "profile_users"
        verbose_name = "User"
        verbose_name_plural = "Users"

class PhoneOTP(models.Model):
    phone = models.CharField(max_length=20)
    otp_code = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    user=models.OneToOneField(ProfileUser,on_delete=models.CASCADE)

    class Meta:
        db_table = "phone_otps"
        verbose_name = "Phone OTP"
        verbose_name_plural = "Phone OTPs"

class EmailOTP(models.Model):
    email = models.CharField(max_length=100)
    otp_code = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    user=models.OneToOneField(ProfileUser,on_delete=models.CASCADE)

    class Meta:
        db_table = "email_otps"
        verbose_name = "Email OTP"
        verbose_name_plural = "Email OTPs"


class AuthenticationCode(models.Model):
    """
    Stores unique authentication codes generated during registration.
    The app saves this code locally and can auto-login without entering details.
    """
    user = models.OneToOneField(ProfileUser, on_delete=models.CASCADE, related_name='auth_code')
    secret_code = models.CharField(max_length=64, unique=True)  # Unique auth token
    user_data = models.JSONField()  # Encrypted: {name, phone, email}
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "authentication_codes"
        verbose_name = "Authentication Code"
        verbose_name_plural = "Authentication Codes"

    @staticmethod
    def generate_code():
        """Generate a unique secret code"""
        return secrets.token_urlsafe(48)

    def __str__(self):
        return f"AuthCode for {self.user.name} ({self.user.phone})"
