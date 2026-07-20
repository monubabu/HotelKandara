from datetime import date
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.hotel.models import Room, RoomType
from .models import Booking

User = get_user_model()

class BookingEngineTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="test_guest", email="guest@test.com", password="pass")
        self.room_type = RoomType.objects.create(name="Deluxe", description="Nice room", price_per_night=100.00)
        self.room = Room.objects.create(room_number="201", room_type=self.room_type, status="available")

        # Create an existing booking from Aug 10 to Aug 15
        Booking.objects.create(
            user=self.user,
            room=self.room,
            check_in=date(2026, 8, 10),
            check_out=date(2026, 8, 15),
            total_price=500.00,
            status="confirmed"
        )
        self.url = reverse('check-availability')

    def test_room_is_unavailable_if_dates_overlap_exactly(self):
        """Dates are exactly matching an existing booking window."""
        response = self.client.get(self.url, {"check_in": "2026-08-10", "check_out": "2026-08-15"})
        self.assertEqual(response.data['available_rooms_count'], 0)

    def test_room_is_unavailable_if_dates_overlap_partially(self):
        """Dates swallow the middle or beginning of the booking window."""
        response = self.client.get(self.url, {"check_in": "2026-08-12", "check_out": "2026-08-18"})
        self.assertEqual(response.data['available_rooms_count'], 0)

    def test_room_is_available_for_completely_separate_dates(self):
        """Dates are entirely out of the current booking bounds."""
        response = self.client.get(self.url, {"check_in": "2026-08-01", "check_out": "2026-08-05"})
        self.assertEqual(response.data['available_rooms_count'], 1)


     def test_authenticated_user_can_create_booking(self):
        # 1. Authenticate user
        self.client.force_authenticate(user=self.user)
        
        # 2. Prepare payload
        payload = {
            "room": self.room.id,
            "check_in": "2026-09-01",
            "check_out": "2026-09-03"
        }
        
        # 3. Post to API
        response = self.client.post(reverse('create-booking'), payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Booking.objects.filter(user=self.user).exists())