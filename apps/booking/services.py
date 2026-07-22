import logging
from django.db import transaction
from rest_framework.exceptions import ValidationError, PermissionDenied

from .models import Booking
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def broadcast_room_update(room, new_status: str, message: str) -> None:
    """
    Broadcasts a real-time WebSocket event to all connected clients.
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'room_availability',
        {
            'type': 'room_status_update',
            'room_id': room.id,
            'room_number': room.room_number,
            'new_status': new_status,
            'message': message
        }
    )


def calculate_booking_price(room, check_in, check_out):
    """
    Calculates total price based on duration and room rate.
    """
    days = (check_out - check_in).days
    return days * room.room_type.price_per_night


def create_booking_service(user, room, check_in, check_out) -> Booking:
    """
    Handles atomic booking creation, price calculation, and real-time event broadcasting.
    """
    total_price = calculate_booking_price(room, check_in, check_out)

    with transaction.atomic():
        booking = Booking.objects.create(
            user=user,
            room=room,
            check_in=check_in,
            check_out=check_out,
            total_price=total_price,
            status='pending'
        )
        logger.info(f"Booking #{booking.id} created for User #{user.id}.")

    # Broadcast WebSocket update
    broadcast_room_update(
        room,
        'pending',
        f"Room {room.room_number} was reserved from {check_in} to {check_out}."
    )

    return booking


def process_payment_service(booking: Booking, user) -> Booking:
    """
    Validates booking ownership/status and processes payment logic.
    """
    if booking.user != user:
        raise PermissionDenied("You do not have permission to pay for this booking.")

    if booking.status != 'pending':
        raise ValidationError(f"Booking cannot be paid for. Current status is '{booking.status}'.")

    booking.status = 'confirmed'
    booking.save()
    logger.info(f"Payment successful for Booking #{booking.id} by User #{user.id}.")
    return booking


def check_in_guest_service(booking: Booking, staff_user) -> Booking:
    """
    Handles front-desk check-in, updates room status to occupied, and broadcasts event.
    """
    if booking.status != 'confirmed':
        raise ValidationError(f"Cannot check-in. Booking status is '{booking.status}', expected 'confirmed'.")

    with transaction.atomic():
        booking.status = 'checked_in'
        booking.save()

        room = booking.room
        room.status = 'occupied'
        room.save()

    logger.info(f"Staff member {staff_user.email} checked in Booking #{booking.id} (Room {room.room_number}).")
    broadcast_room_update(room, 'occupied', f"Room {room.room_number} is now occupied.")

    return booking


def check_out_guest_service(booking: Booking, staff_user) -> Booking:
    """
    Handles front-desk check-out, updates room status to cleaning, and broadcasts event.
    """
    if booking.status != 'checked_in':
        raise ValidationError(f"Cannot check-out. Booking status is '{booking.status}', expected 'checked_in'.")

    with transaction.atomic():
        booking.status = 'checked_out'
        booking.save()

        room = booking.room
        room.status = 'cleaning'
        room.save()

    logger.info(f"Staff member {staff_user.email} checked out Booking #{booking.id}. Room set to cleaning.")
    broadcast_room_update(room, 'cleaning', f"Room {room.room_number} is now undergoing cleaning.")

    return booking