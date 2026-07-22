from rest_framework import generics
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import Room
from .serializers import RoomSerializer


@extend_schema(
    summary="List Available Rooms",
    description="Public endpoint to fetch a paginated list of all currently available rooms with their associated room types.",
    tags=["Hotel Rooms"],
    responses={
        200: RoomSerializer(many=True),
    }
)
class RoomListView(generics.ListAPIView):
    """
    Public GET API endpoint to fetch all rooms(paginated).
    Anyone can access this endpoint to browse the hotel selection.
    """
    queryset = Room.objects.filter(status='available').select_related('room_type')
    serializer_class = RoomSerializer
    permission_classes = [AllowAny]


@extend_schema(
    summary="Retrieve Room Details",
    description="Public endpoint to fetch details of a specific physical room by its primary key ID.",
    tags=["Hotel Rooms"],
    responses={
        200: RoomSerializer,
        404: OpenApiResponse(description="Room not found.")
    }
)
class RoomDetailView(generics.RetrieveAPIView):
    """
    Public GET API endpoint to fetch detail metrics of a single physical room.
    """
    queryset = Room.objects.all().select_related('room_type')
    serializer_class = RoomSerializer
    permission_classes = [AllowAny]