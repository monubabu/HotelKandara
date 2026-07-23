from django.contrib import admin
from django.utils.html import format_html

from .models import Amenity, RoomType, Room


# Amenity Admin
@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "icon_name",
    )

    search_fields = (
        "name",
        "icon_name",
    )

    ordering = (
        "name",
    )

    list_per_page = 20



# Room Type Admin
@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "price_per_night",
        "max_capacity",
        "total_rooms",
        "amenities_list",
        "image_preview",
    )

    search_fields = (
        "name",
        "description",
    )

    list_filter = (
        "max_capacity",
    )

    ordering = (
        "price_per_night",
    )

    filter_horizontal = (
        "amenities",
    )

    list_per_page = 20

    readonly_fields = (
        "image_preview",
    )

    fieldsets = (
        (
            "Room Information",
            {
                "fields": (
                    "name",
                    "description",
                    "price_per_night",
                    "max_capacity",
                )
            },
        ),
        (
            "Amenities",
            {
                "fields": (
                    "amenities",
                )
            },
        ),
        (
            "Image",
            {
                "fields": (
                    "image",
                    "image_preview",
                )
            },
        ),
    )

    @admin.display(description="Amenities")
    def amenities_list(self, obj):
        return ", ".join(
            amenity.name for amenity in obj.amenities.all()
        ) or "-"

    @admin.display(description="Rooms")
    def total_rooms(self, obj):
        return obj.rooms.count()

    @admin.display(description="Image")
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="120" style="border-radius:8px;" />',
                obj.image.url,
            )
        return "-"


# Room Admin
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        "room_number",
        "room_type",
        "floor",
        "colored_status",
    )

    search_fields = (
        "room_number",
        "room_type__name",
    )

    list_filter = (
        "status",
        "floor",
        "room_type",
    )

    ordering = (
        "room_number",
    )

    autocomplete_fields = (
        "room_type",
    )

    list_per_page = 25

    actions = (
        "mark_available",
        "mark_cleaning",
        "mark_maintenance",
    )

    fieldsets = (
        (
            "Room Details",
            {
                "fields": (
                    "room_number",
                    "room_type",
                    "floor",
                    "status",
                )
            },
        ),
    )

    @admin.display(description="Status")
    def colored_status(self, obj):
        colors = {
            "available": "#28a745",
            "occupied": "#dc3545",
            "cleaning": "#fd7e14",
            "maintenance": "#6c757d",
        }

        return format_html(
            '<strong style="color:{};">{}</strong>',
            colors.get(obj.status, "#000"),
            obj.get_status_display(),
        )

    @admin.action(description="Mark selected rooms as Available")
    def mark_available(self, request, queryset):
        updated = queryset.update(status="available")
        self.message_user(
            request,
            f"{updated} room(s) marked as Available."
        )

    @admin.action(description="Mark selected rooms as Under Cleaning")
    def mark_cleaning(self, request, queryset):
        updated = queryset.update(status="cleaning")
        self.message_user(
            request,
            f"{updated} room(s) marked as Under Cleaning."
        )

    @admin.action(description="Mark selected rooms as Under Maintenance")
    def mark_maintenance(self, request, queryset):
        updated = queryset.update(status="maintenance")
        self.message_user(
            request,
            f"{updated} room(s) marked as Under Maintenance."
        )