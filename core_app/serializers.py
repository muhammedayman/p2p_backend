from rest_framework import serializers
from .models import ProfileUser

class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileUser
        fields = ['name', 'phone', 'email', 'photo', 'is_photo_public']

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
