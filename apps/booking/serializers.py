from rest_framework import serializers
from .models import Booking
from .utils import get_available_rooms
from datetime import datetime

class BookingSerializer(serializers.ModelSerializer):
      class Meta:
            model = Booking
            fields = ['id', 'room','check_in','check_out','total_price','status']
            read_only_fields = ['total_price','status']

      def validate(self, data):
            check_in = data['check_in']
            check_out = data['check_out']
            room = data['room']

            # Date logic
            if check_in >= check_out:
                  raise serializers.ValidationError("Check-out must be after check-in.")
            
            # Reverify availability
            available_rooms = get_available_rooms(check_in, check_out)
            if room not in available_rooms:
                  raise serializers.ValidationError("These room is no longer available for these dates.")
            
            return data
      