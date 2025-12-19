from rest_framework import serializers
from .models import ProfileUser, AuthenticationCode

class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileUser
        fields = ['name', 'phone', 'email', 'photo', 'is_photo_public']

class AuthenticationCodeSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField()
    
    class Meta:
        model = AuthenticationCode
        fields = ['secret_code', 'user_details', 'created_at', 'last_used']
    
    def get_user_details(self, obj):
        return {
            'name': obj.user.name,
            'phone': obj.user.phone,
            'email': obj.user.email
        }

class UserDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for returning full user details after authentication.
    """
    is_online = serializers.SerializerMethodField()
    
    class Meta:
        model = ProfileUser
        fields = ['id', 'name', 'phone', 'email', 'photo', 'is_photo_public', 
                  'is_phone_verified', 'is_email_verified', 'is_online', 'last_seen']
    
    def get_is_online(self, obj):
        return obj.is_online()

class PeerSerializer(serializers.ModelSerializer):
    """
    Serializer for Discovery. 
    STRIPS sensitive info (phone, email).
    HANDLES Photo privacy logic.
    """
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = ProfileUser
        fields = ['id', 'name', 'ip', 'port', 'photo_url']
    
    def get_photo_url(self, obj):
        if obj.is_photo_public:
            return obj.photo
        return None  # Private photo
