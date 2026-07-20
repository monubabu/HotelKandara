from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Amenity, RoomType, Room

class HotelInventoryTests(APITestCase):

    def setUp(self):
        # 1. Create mock Amenity
        self.wifi = Amenity.objects.create(name="Free Wi-Fi", icon_name="fa-wifi")
        
        # 2. Create mock Room Type
        self.deluxe_type = RoomType.objects.create(
            name="Deluxe Suite",
            description="A spacious suite with beautiful views",
            price_per_night=150.00,
            max_capacity=2
        )
        self.deluxe_type.amenities.add(self.wifi)
        
        # 3. Create mock Physical Rooms
        self.available_room = Room.objects.create(
            room_number="101",
            room_type=self.deluxe_type,
            floor=1,
            status="available"
        )
        self.dirty_room = Room.objects.create(
            room_number="102",
            room_type=self.deluxe_type,
            floor=1,
            status="cleaning" # Should not appear in the room list
        )

    def test_get_room_list_only_returns_available_rooms(self):
        """
        Verify that our catalog listing returns only active/available rooms.
        """
        url = reverse('room-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only find 1 available room (excluding the "cleaning" room)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['room_number'], "101")
        self.assertEqual(response.data[0]['room_type']['name'], "Deluxe Suite")

    def test_get_room_detail_successful(self):
        """
        Verify that querying details for a specific room returns correct nested values.
        """
        url = reverse('room-detail', kwargs={'pk': self.available_room.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['room_number'], "101")
        # Ensure amenities list is correctly serialized and nested
        self.assertEqual(response.data['room_type']['amenities'][0]['name'], "Free Wi-Fi")