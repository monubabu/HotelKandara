from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied

from apps.hotel.models import Room, RoomType
from .models import Booking
from .services import (
    calculate_booking_price,
    create_booking_service,
    process_payment_service,
    check_in_guest_service,
    check_out_guest_service
)

User = get_user_model()


class BookingServiceAndAPIViewsTestCase(TestCase):

    def setUp(self):
        # Create test users
        self.guest_user = User.objects.create_user(
            username="guest@example.com",
            email="guest@example.com",
            password="password123"
        )
        self.other_guest = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="password123"
        )
        self.staff_user = User.objects.create_user(
            username="receptionist@example.com",
            email="receptionist@example.com",
            password="password123",
            is_staff=True
        )

        # Create room type and room matching hotel models
        self.room_type = RoomType.objects.create(
            name="Deluxe Suite",
            description="A spacious room with a view.",
            price_per_night=100.00,
            max_capacity=2
        )
        self.room = Room.objects.create(
            room_number="101",
            room_type=self.room_type,
            floor=1,
            status="available"
        )

        # Dates setup
        self.check_in = date.today() + timedelta(days=1)
        self.check_out = date.today() + timedelta(days=4)  # 3 nights stay

        # Initialize DRF API Client
        self.client = APIClient()

    # ==========================================
    # 1. SERVICE LAYER TESTS
    # ==========================================

    def test_calculate_booking_price(self):
        """Test calculation of total room price based on nights stay."""
        price = calculate_booking_price(self.room, self.check_in, self.check_out)
        self.assertEqual(price, 300.00)

    @patch("apps.booking.services.broadcast_room_update")
    def test_create_booking_service(self, mock_broadcast):
        """Test service creates a booking record with correct total price and calls WebSocket broadcast."""
        booking = create_booking_service(
            user=self.guest_user,
            room=self.room,
            check_in=self.check_in,
            check_out=self.check_out
        )

        self.assertEqual(booking.user, self.guest_user)
        self.assertEqual(booking.room, self.room)
        self.assertEqual(booking.total_price, 300.00)
        self.assertEqual(booking.status, 'pending')
        mock_broadcast.assert_called_once()

    def test_process_payment_service_success(self):
        """Test successful payment updates booking status to confirmed."""
        booking = Booking.objects.create(
            user=self.guest_user,
            room=self.room,
            check_in=self.check_in,
            check_out=self.check_out,
            total_price=300.00,
            status='pending'
        )
        updated_booking = process_payment_service(booking, self.guest_user)
        self.assertEqual(updated_booking.status, 'confirmed')

    def test_process_payment_service_permission_denied(self):
        """Test that a user cannot pay for another guest's booking."""
        booking = Booking.objects.create(
            user=self.guest_user,
            room=self.room,
            check_in=self.check_in,
            check_out=self.check_out,
            total_price=300.00,
            status='pending'
        )
        with self.assertRaises(PermissionDenied):
            process_payment_service(booking, self.other_guest)

    @patch("apps.booking.services.broadcast_room_update")
    def test_check_in_guest_service(self, mock_broadcast):
        """Test staff check-in updates booking to 'checked_in' and room to 'occupied'."""
        booking = Booking.objects.create(
            user=self.guest_user,
            room=self.room,
            check_in=self.check_in,
            check_out=self.check_out,
            total_price=300.00,
            status='confirmed'
        )
        updated_booking = check_in_guest_service(booking, self.staff_user)

        self.assertEqual(updated_booking.status, 'checked_in')
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, 'occupied')
        mock_broadcast.assert_called_once()

    @patch("apps.booking.services.broadcast_room_update")
    def test_check_out_guest_service(self, mock_broadcast):
        """Test staff check-out updates booking to 'checked_out' and room to 'cleaning'."""
        booking = Booking.objects.create(
            user=self.guest_user,
            room=self.room,
            check_in=self.check_in,
            check_out=self.check_out,
            total_price=300.00,
            status='checked_in'
        )
        updated_booking = check_out_guest_service(booking, self.staff_user)

        self.assertEqual(updated_booking.status, 'checked_out')
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, 'cleaning')
        mock_broadcast.assert_called_once()

    # ==========================================
    # 2. API VIEW TESTS
    # ==========================================

    def test_check_availability_view_success(self):
        """Test GET availability endpoint returning available rooms."""
        url = reverse('check-availability')
        response = self.client.get(url, {
            'check_in': str(self.check_in),
            'check_out': str(self.check_out)
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['available_rooms_count'], 1)

    def test_check_availability_invalid_dates(self):
        """Test GET returns 400 Bad Request when check-out is before check-in."""
        url = reverse('check-availability')
        response = self.client.get(url, {
            'check_in': str(self.check_out),
            'check_out': str(self.check_in)
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.booking.services.broadcast_room_update")
    def test_create_booking_view_authenticated(self, mock_broadcast):
        """Test authenticated user creating a booking via POST."""
        self.client.force_authenticate(user=self.guest_user)
        url = reverse('create-booking')
        payload = {
            "room": self.room.id,
            "check_in": str(self.check_in),
            "check_out": str(self.check_out)
        }
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("booking_id", response.data)
        self.assertEqual(response.data["total_price"], 300.00)

    def test_create_booking_view_unauthenticated(self):
        """Test unauthenticated user gets 401 Unauthorized when creating a booking."""
        url = reverse('create-booking')
        payload = {
            "room": self.room.id,
            "check_in": str(self.check_in),
            "check_out": str(self.check_out)
        }
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_check_in_view_forbidden_for_regular_user(self):
        """Test non-staff user gets 403 Forbidden when calling staff check-in."""
        booking = Booking.objects.create(
            user=self.guest_user,
            room=self.room,
            check_in=self.check_in,
            check_out=self.check_out,
            total_price=300.00,
            status='confirmed'
        )
        self.client.force_authenticate(user=self.guest_user)
        url = reverse('staff-check-in', kwargs={'booking_id': booking.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# test case for schema
class SchemaTests(APITestCase):

    def test_schema_endpoint(self):
        response = self.client.get(reverse("schema"))
        self.assertEqual(response.status_code,200)

    def test_swagger_ui(self):
        response = self.client.get(reverse("swagger-ui"))
        self.assertEqual(response.status_code,200)

    def test_redoc_ui(self):
        response = self.client.get(reverse("redoc"))
        self.assertEqual(response.status_code,200)