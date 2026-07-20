from rest_framework import generics
from rest_framework.permissions import AllowAny
from .models import Room
from .serializers import RoomSerializer

class RoomListView(generics.ListAPIView):
      """
      Public GET API endpoint to fetch all rooms(paginated).
      Anyone cna access this endpoint to browse the hotel selection
      """
      queryset = Room.objects.filter(status='available').select_related('room_type')
      serializer_class = RoomSerializer
      permission_classes = [AllowAny]


class RoomDetailView(generics.RetrieveAPIView):
      '''
      Public GET API endpoint to fetch detail metrics of a single physical room.
      '''
      queryset = Room.objects.all().select_related('room_type')
      serializer_class = RoomSerializer
      permission_classes = [AllowAny]
      
