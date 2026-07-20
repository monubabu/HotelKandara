import logging
from datetime import datetime
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.hotel.serializers import RoomSerializer
from .models import Booking
from .serializers import BookingSerializer
from .utils import get_available_rooms
from .permissions import IsStaffUser

logger = logging.getLogger(__name__)


# ==========================================
# GUEST ENDPOINTS
# ==========================================

class CheckAvailabilityView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        check_in_str = request.query_params.get('check_in')
        check_out_str = request.query_params.get('check_out')

        if not check_in_str or not check_out_str:
            logger.warning("Availability check failed: Missing date parameters.")
            return Response(
                {"error": "Both 'check_in' and 'check_out' query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            check_in_date = datetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        except ValueError:
            logger.warning(f"Availability check failed: Invalid date format received ({check_in_str}, {check_out_str}).")
            return Response(
                {"error": "Invalid date format. Expected YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if check_in_date >= check_out_date:
            return Response(
                {"error": "Check-out date must be strictly after check-in date."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            available_rooms = get_available_rooms(check_in_date, check_out_date)
            serializer = RoomSerializer(available_rooms, many=True, context={'request': request})
            
            return Response({
                "check_in": check_in_str,
                "check_out": check_out_str,
                "available_rooms_count": len(serializer.data),
                "results": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Unexpected error during availability search: {str(e)}", exc_info=True)
            return Response(
                {"error": "An unexpected server error occurred while searching for rooms."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BookingCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BookingSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    check_in = serializer.validated_data['check_in']
                    check_out = serializer.validated_data['check_out']
                    room = serializer.validated_data['room']
                    
                    days = (check_out - check_in).days
                    total_price = days * room.room_type.price_per_night

                    booking = serializer.save(
                        user=request.user,
                        total_price=total_price,
                        status='pending'
                    )
                    
                    logger.info(f"Booking #{booking.id} created successfully by User #{request.user.id}.")

                return Response({
                    "message": "Booking request created successfully. Proceed to payment.",
                    "booking_id": booking.id,
                    "total_price": total_price
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                logger.error(f"Failed to complete booking transaction for User #{request.user.id}: {str(e)}", exc_info=True)
                return Response(
                    {"error": "Could not complete booking due to a server error."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
        errors = serializer.errors
        if 'room' in errors or 'non_field_errors' in errors:
            logger.warning(f"Booking conflict for User #{request.user.id}: {errors}")
            return Response(errors, status=status.HTTP_409_CONFLICT)

        return Response(errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentMockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id, user=request.user)

            if booking.status != 'pending':
                return Response(
                    {"error": f"Booking cannot be paid for. Current status is '{booking.status}'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Simulate payment processing
            booking.status = 'confirmed'
            booking.save()

            logger.info(f"Payment successful for Booking #{booking.id} by User #{request.user.id}.")

            return Response({
                "message": "Payment successful! Booking confirmed.",
                "booking_id": booking.id,
                "status": booking.status
            }, status=status.HTTP_200_OK)

        except Booking.DoesNotExist:
            logger.warning(f"Payment failed: Booking #{booking_id} not found for User #{request.user.id}.")
            return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)


# ==========================================
# STAFF / RECEPTIONIST ENDPOINTS
# ==========================================

class StaffBookingListView(APIView):
    permission_classes = [IsStaffUser]

    def get(self, request):
        bookings = Booking.objects.filter(
            status__in=['confirmed', 'checked_in']
        ).select_related('user', 'room', 'room__room_type').order_by('check_in')
        
        serializer = BookingSerializer(bookings, many=True)
        return Response({"count": len(serializer.data), "bookings": serializer.data}, status=status.HTTP_200_OK)


class StaffCheckInView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id)

            if booking.status != 'confirmed':
                return Response(
                    {"error": f"Cannot check-in. Booking status is currently '{booking.status}', expected 'confirmed'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            with transaction.atomic():
                booking.status = 'checked_in'
                booking.save()
                
                room = booking.room
                room.status = 'occupied'
                room.save()

            logger.info(f"Staff member {request.user.email} checked in Booking #{booking.id} (Room {room.room_number}).")
            
            return Response({
                "message": f"Guest checked in successfully to Room {room.room_number}.",
                "booking_id": booking.id,
                "status": booking.status
            }, status=status.HTTP_200_OK)

        except Booking.DoesNotExist:
            return Response({"error": "Booking ID not found."}, status=status.HTTP_404_NOT_FOUND)


class StaffCheckOutView(APIView):
    permission_classes = [IsStaffUser]

    def post(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id)

            if booking.status != 'checked_in':
                return Response(
                    {"error": f"Cannot check-out. Booking status is '{booking.status}', expected 'checked_in'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            with transaction.atomic():
                booking.status = 'checked_out'
                booking.save()
                
                room = booking.room
                room.status = 'cleaning'
                room.save()

            logger.info(f"Staff member {request.user.email} checked out Booking #{booking.id}. Room {room.room_number} set to cleaning.")

            return Response({
                "message": f"Guest checked out. Room {room.room_number} is now marked for housekeeping.",
                "booking_id": booking.id,
                "status": booking.status
            }, status=status.HTTP_200_OK)

        except Booking.DoesNotExist:
            return Response({"error": "Booking ID not found."}, status=status.HTTP_404_NOT_FOUND)