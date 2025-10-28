from rest_framework import serializers
from apps.news.models import New
from apps.events.models import Event
from django.utils.timezone import now


class NewSerializer(serializers.ModelSerializer):

    cover_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = New
        fields = ['pk', 'title', 'description', 'cover_image', 'dynamic_link', 'expired_at', 'status', 'cover_image_url', 'event']
        read_only_fields = ['dynamic_link', 'pk']
    
    def get_cover_image_url(self, obj):
        if obj.cover_image:
            return obj.cover_image.url
        return None
    

class NewCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = New
        fields = ['pk','title', 'description', 'cover_image', 'expired_at', 'status', 'event']
        read_only_fields = ['pk']
