from django.contrib import admin
from django.utils.html import format_html

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "guest_email",
        "room",
        "booking_period",
        "total_price",
        "colored_status",
        "created_at",
    )

    list_filter = (
        "status",
        "check_in",
        "check_out",
        "created_at",
        "room__room_type",
    )

    search_fields = (
        "id",
        "user__email",
        "user__username",
        "room__room_number",
    )

    ordering = ("-created_at",)

    autocomplete_fields = (
        "user",
        "room",
    )

    list_select_related = (
        "user",
        "room",
        "room__room_type",
    )

    readonly_fields = (
        "total_price",
        "created_at",
        "updated_at",
    )

    date_hierarchy = "check_in"

    list_per_page = 25

    actions = (
        "mark_confirmed",
        "mark_checked_in",
        "mark_checked_out",
        "mark_cancelled",
    )

    fieldsets = (
        (
            "Guest Information",
            {
                "fields": (
                    "user",
                    "room",
                )
            },
        ),
        (
            "Booking Details",
            {
                "fields": (
                    "check_in",
                    "check_out",
                    "total_price",
                    "status",
                )
            },
        ),
        (
            "System Information",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    # -----------------------------
    # Custom Columns
    # -----------------------------

    @admin.display(description="Guest")
    def guest_email(self, obj):
        return format_html(
            '<strong>{}</strong>',
            obj.user.email,
        )

    @admin.display(description="Stay")
    def booking_period(self, obj):
        return f"{obj.check_in} → {obj.check_out}"

    @admin.display(description="Status")
    def colored_status(self, obj):
        colors = {
            "pending": "#ff9800",
            "confirmed": "#2196f3",
            "checked_in": "#4caf50",
            "checked_out": "#607d8b",
            "cancelled": "#f44336",
        }

        return format_html(
            '<span style="padding:4px 8px;border-radius:6px;background:{};color:white;font-weight:bold;">{}</span>',
            colors.get(obj.status, "#666"),
            obj.get_status_display(),
        )

    # -----------------------------
    # Admin Actions
    # -----------------------------

    @admin.action(description="Mark selected bookings as Confirmed")
    def mark_confirmed(self, request, queryset):
        queryset.update(status="confirmed")

    @admin.action(description="Mark selected bookings as Checked In")
    def mark_checked_in(self, request, queryset):
        queryset.update(status="checked_in")

    @admin.action(description="Mark selected bookings as Checked Out")
    def mark_checked_out(self, request, queryset):
        queryset.update(status="checked_out")

    @admin.action(description="Mark selected bookings as Cancelled")
    def mark_cancelled(self, request, queryset):
        queryset.update(status="cancelled")

    # -----------------------------
    # Permissions
    # -----------------------------

    def has_add_permission(self, request):
        """
        Prevent manual booking creation from Django admin.
        Bookings should be created via the website/API.
        """
        return False