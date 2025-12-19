from django.urls import path
from .views import (
    RegisterView, VerifySMSWebhookView, 
    EmailOTPRequestView, EmailOTPVerifyView, UserStatusView,
    HeartbeatView, PeersListView, TURNCredentialsView,
    LoginWithSecretCodeView, VerifySecretCodeView
)

urlpatterns = [
    # Auth
    path('register/', RegisterView.as_view()),
    path('verify-sms/', VerifySMSWebhookView.as_view()),
    path('email-otp/request/', EmailOTPRequestView.as_view()),
    path('email-otp/verify/', EmailOTPVerifyView.as_view()),
    path('status/', UserStatusView.as_view()),
    path('login-with-code/', LoginWithSecretCodeView.as_view()),  # Auto-login with secret code
    path('verify-code/', VerifySecretCodeView.as_view()),  # Verify code validity
    
    # Signaling
    path('heartbeat/', HeartbeatView.as_view()),
    path('peers/', PeersListView.as_view()),
    path('turn-creds/', TURNCredentialsView.as_view()),
]
