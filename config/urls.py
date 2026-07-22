from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("apps.users.urls")),
    path("api/hotel/", include("apps.hotel.urls")),
    path('api/bookings/', include('apps.booking.urls')),

    path("api/schema/", SpectacularAPIView.as_view(),name='schema'),
    path("api/docs/swagger/", SpectacularSwaggerView.as_view(url_name='schema'),name='swagger-ui'),
    path("api/docs/redoc/",SpectacularRedocView.as_view(url_name='schema'),name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)