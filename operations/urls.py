from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, ResourceViewSet, BookingViewSet

router = DefaultRouter()
router.register(r'events', EventViewSet, basename='event')
router.register(r'resources', ResourceViewSet, basename='resource')
router.register(r'bookings', BookingViewSet, basename='booking')

urlpatterns = [
    path('', include(router.urls)),
]
