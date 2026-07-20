from django.urls import path
from .views import (
    CheckAvailabilityView,
    BookingCreateView,
    PaymentMockView,
    StaffBookingListView,
    StaffCheckInView,
    StaffCheckOutView
)

urlpatterns = [
    # Guest Endpoints
    path('check-availability/', CheckAvailabilityView.as_view(), name='check-availability'),
    path('create/', BookingCreateView.as_view(), name='create-booking'),
    path('pay/<int:booking_id>/', PaymentMockView.as_view(), name='process-payment'),

    # Staff / Receptionist Endpoints
    path('staff/dashboard/', StaffBookingListView.as_view(), name='staff-dashboard'),
    path('staff/check-in/<int:booking_id>/', StaffCheckInView.as_view(), name='staff-check-in'),
    path('staff/check-out/<int:booking_id>/', StaffCheckOutView.as_view(), name='staff-check-out'),
]