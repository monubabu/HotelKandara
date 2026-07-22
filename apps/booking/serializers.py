from django.utils import timezone
from rest_framework import serializers
#from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from .models import Booking
from .utils import get_available_rooms


class BookingSerializer(serializers.ModelSerializer):

    class Meta:
        model = Booking
        fields = "__all__"
        read_only_fields = (
            "user",
            "status",
            "total_price",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        check_in = attrs["check_in"]
        check_out = attrs["check_out"]
        room = attrs["room"]

        today = timezone.localdate()

        # Check-in cannot be in the past
        if check_in < today:
            raise serializers.ValidationError({
                "check_in": "Check-in date cannot be in the past."
            })

        # Check-out must be after check-in
        if check_out <= check_in:
            raise serializers.ValidationError({
                "check_out": "Check-out date must be after check-in."
            })

        # Maximum stay: 30 nights
        if (check_out - check_in).days > 30:
            raise serializers.ValidationError({
                "check_out": "Maximum booking duration is 30 nights."
            })

        # Room must be available
        available_rooms = get_available_rooms(check_in, check_out)

        if not available_rooms.filter(pk=room.pk).exists():
            raise serializers.ValidationError({
                "room": "This room is not available for the selected dates."
            })

        return attrs

