from django.db.models import Q
from .models import Booking
from apps.hotel.models import Room

def get_available_rooms(check_in_date, check_out_date):
    """
    Returns a queryset of rooms that are NOT occupied, in maintenance, 
    or booked during the requested date window.
    """
    # 1. Find all active bookings that overlap with the user's requested window
    overlapping_bookings = Booking.objects.filter(
        status__in=['pending', 'confirmed', 'checked_in']
    ).filter(
        # Logic: A booking overlaps if its check-in is before our check-out 
        # AND its check-out is after our check-in.
        Q(check_in__lt=check_out_date) & Q(check_out__gt=check_in_date)
    )

    # 2. Extract the room IDs from those unavailable bookings
    booked_room_ids = overlapping_bookings.values_list('room_id', flat=True)

    # 3. Filter our inventory to get rooms that are marked 'available' AND not in the booked list
    available_rooms = Room.objects.filter(
        status='available'
    ).exclude(
        id__in=booked_room_ids
    ).select_related('room_type')

    return available_rooms

