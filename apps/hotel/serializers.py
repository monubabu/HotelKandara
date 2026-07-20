from rest_framework import serializers
from .models import Amenity, RoomType, Room

class AmenitySerializer(serializers.ModelSerializer):
      class Meta:
            model = Amenity
            fields = ['id','name','icon_name']

class RoomTypeSerializer(serializers.ModelSerializer):
      # Nested representation of amenties inside RoomType
      amenities = AmenitySerializer(many =True, read_only=True)
      image_url = serializers.SerializerMethodField()

      class Meta:
            model = RoomType
            fields = ['id','name','description','price_per_night','max_capacity','amenities','image_url']

      def get_image_url(self,obj):
            # Generates a full HTTP path to the image
            request = self.context.get('request')
            if obj.image and request:
                  return request.build_absolut_uri(obj.image.url)
            return None
      
class RoomSerializer(serializers.ModelSerializer):
      # Deeply serialize RoomType inside Room View
      room_type = RoomTypeSerializer(read_only=True)

      class Meta:
            model = Room
            fields = ['id','room_number','room_type','floor','status']

      

