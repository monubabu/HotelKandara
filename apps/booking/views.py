import logging
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError, PermissionDenied

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
    inline_serializer,
    OpenApiExample
)
from rest_framework import serializers

from apps.hotel.serializers import RoomSerializer
from .models import Booking
from .serializers import BookingSerializer
from .utils import get_available_rooms
from .permissions import IsStaffUser
from .services import (
    create_booking_service,
    process_payment_service,
    check_in_guest_service,
    check_out_guest_service
)

logger = logging.getLogger(__name__)


# ==========================================
# GUEST ENDPOINTS
# ==========================================

class CheckAvailabilityView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Check Room Availability",
        description="Check available rooms for a specified check-in and check-out date range.",
        parameters=[
            OpenApiParameter(
                name="check_in",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Check-in date (YYYY-MM-DD)"
            ),
            OpenApiParameter(
                name="check_out",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Check-out date (YYYY-MM-DD)"
                
            ),
        ],
        responses={
            200: inline_serializer(
                name="CheckAvailabilityResponse",
                fields={
                    "check_in": serializers.CharField(),
                    "check_out": serializers.CharField(),
                    "available_rooms_count": serializers.IntegerField(),
                    "results": RoomSerializer(many=True)
                }
            ),
            400: OpenApiResponse(description="Missing parameters, invalid date format, or check-out before check-in.")
        },
        tags=["Bookings - Guest"]
    )
    def get(self, request):
        check_in_str = request.query_params.get('check_in')
        check_out_str = request.query_params.get('check_out')

        if not check_in_str or not check_out_str:
            return Response(
                {"error": "Both 'check_in' and 'check_out' query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            check_in_date = datetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Expected YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if check_in_date >= check_out_date:
            return Response(
                {"error": "Check-out date must be strictly after check-in date."},
                status=status.HTTP_400_BAD_REQUEST
            )

        available_rooms = get_available_rooms(check_in_date, check_out_date)
        serializer = RoomSerializer(available_rooms, many=True, context={'request': request})
        
        return Response({
            "check_in": check_in_str,
            "check_out": check_out_str,
            "available_rooms_count": len(serializer.data),
            "results": serializer.data
        }, status=status.HTTP_200_OK)


class BookingCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Create a Booking Reservation",
        description="Creates a pending booking reservation for the authenticated guest.",
        request=BookingSerializer,
        responses={
            201: inline_serializer(
                name="BookingCreateSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "booking_id": serializers.IntegerField(),
                    "total_price": serializers.DecimalField(max_digits=10, decimal_places=2)
                }
            ),
            400: OpenApiResponse(description="Validation error in submitted fields."),
            409: OpenApiResponse(description="Room already booked for selected dates."),
            500: OpenApiResponse(description="Internal server error during booking process.")
        },
        tags=["Bookings - Guest"]
    )
    def post(self, request):
        serializer = BookingSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                booking = create_booking_service(
                    user=request.user,
                    room=serializer.validated_data['room'],
                    check_in=serializer.validated_data['check_in'],
                    check_out=serializer.validated_data['check_out']
                )

                return Response({
                    "message": "Booking request created successfully. Proceed to payment.",
                    "booking_id": booking.id,
                    "total_price": booking.total_price
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                logger.error(f"Error creating booking for User #{request.user.id}: {str(e)}", exc_info=True)
                return Response({"error": "Could not complete booking."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        errors = serializer.errors
        if 'room' in errors or 'non_field_errors' in errors:
            return Response(errors, status=status.HTTP_409_CONFLICT)

        return Response(errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentMockView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Process Payment for Booking",
        description="Mocks payment processing for a pending booking and confirms reservation upon success.",
        parameters=[
            OpenApiParameter(
                name="booking_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the booking to pay for",
                required=True
            )
        ],
        request = None,
        responses={
            200: inline_serializer(
                name="PaymentSuccessResponse",
                fields={
                    "message": serializers.CharField(),
                    "booking_id": serializers.IntegerField(),
                    "status": serializers.CharField()
                }
            ),
            400: OpenApiResponse(description="Invalid payment request or permission denied."),
            404: OpenApiResponse(description="Booking ID not found.")
        },
        tags=["Bookings - Guest"],

        
    )
    def post(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id)
            booking = process_payment_service(booking, request.user)

            return Response({
                "message": "Payment successful! Booking confirmed.",
                "booking_id": booking.id,
                "status": booking.status
            }, status=status.HTTP_200_OK)

        except Booking.DoesNotExist:
            return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)
        except (ValidationError, PermissionDenied) as e:
            return Response({"error": e.detail if hasattr(e, 'detail') else str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# STAFF ENDPOINTS
# ==========================================

class StaffBookingListView(APIView):
    permission_classes = [IsStaffUser]

    @extend_schema(
        summary="List Active Bookings (Staff Dashboard)",
        description="Retrieves a list of all confirmed and checked-in bookings for staff management.",
        responses={
            200: inline_serializer(
                name="StaffBookingListResponse",
                fields={
                    "count": serializers.IntegerField(),
                    "bookings": BookingSerializer(many=True)
                }
            ),
            403: OpenApiResponse(description="Forbidden - Requires staff privileges.")
        },
        tags=["Bookings - Staff"]
    )
    def get(self, request):
        bookings = Booking.objects.filter(
            status__in=['confirmed', 'checked_in']
        ).select_related('user', 'room', 'room__room_type').order_by('check_in')
        
        serializer = BookingSerializer(bookings, many=True)
        return Response({"count": len(serializer.data), "bookings": serializer.data}, status=status.HTTP_200_OK)


class StaffCheckInView(APIView):
    permission_classes = [IsStaffUser]

    @extend_schema(
        summary="Check In Guest",
        description="Performs guest check-in for a confirmed booking and sets room status to occupied.",
        parameters=[
            OpenApiParameter(
                name="booking_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the booking to check in",
                required=True
            )
        ],
        request = None,
        responses={
            200: inline_serializer(
                name="StaffCheckInResponse",
                fields={
                    "message": serializers.CharField(),
                    "booking_id": serializers.IntegerField(),
                    "status": serializers.CharField()
                }
            ),
            400: OpenApiResponse(description="Invalid check-in state or date validation failed."),
            403: OpenApiResponse(description="Forbidden - Requires staff privileges."),
            404: OpenApiResponse(description="Booking ID not found.")
        },
        tags=["Bookings - Staff"]
    )
    def post(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id)
            booking = check_in_guest_service(booking, request.user)

            return Response({
                "message": f"Guest checked in successfully to Room {booking.room.room_number}.",
                "booking_id": booking.id,
                "status": booking.status
            }, status=status.HTTP_200_OK)

        except Booking.DoesNotExist:
            return Response({"error": "Booking ID not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({"error": e.detail if hasattr(e, 'detail') else str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StaffCheckOutView(APIView):
    permission_classes = [IsStaffUser]

    @extend_schema(
        summary="Check Out Guest",
        description="Performs guest check-out for an active stay and flags room status for cleaning.",
        parameters=[
            OpenApiParameter(
                name="booking_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the booking to check out",
                required=True
            )
        ],
        request = None,
        responses={
            200: inline_serializer(
                name="StaffCheckOutResponse",
                fields={
                    "message": serializers.CharField(),
                    "booking_id": serializers.IntegerField(),
                    "status": serializers.CharField()
                }
            ),
            400: OpenApiResponse(description="Invalid check-out state validation."),
            403: OpenApiResponse(description="Forbidden - Requires staff privileges."),
            404: OpenApiResponse(description="Booking ID not found.")
        },
        tags=["Bookings - Staff"]
    )
    def post(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id)
            booking = check_out_guest_service(booking, request.user)

            return Response({
                "message": f"Guest checked out. Room {booking.room.room_number} is now marked for housekeeping.",
                "booking_id": booking.id,
                "status": booking.status
            }, status=status.HTTP_200_OK)

        except Booking.DoesNotExist:
            return Response({"error": "Booking ID not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({"error": e.detail if hasattr(e, 'detail') else str(e)}, status=status.HTTP_400_BAD_REQUEST)