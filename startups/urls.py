from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StartupViewSet, IdeaViewSet, PhaseViewSet, MilestoneViewSet, MeetingListCreateView, MeetingRetrieveUpdateDestroyView

router = DefaultRouter()
router.register(r'startups', StartupViewSet)
router.register(r'ideas', IdeaViewSet)
router.register(r'phases', PhaseViewSet)
router.register(r'milestones', MilestoneViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('meetings/', MeetingListCreateView.as_view(), name='meeting-list'),
    path('meetings/<int:pk>/', MeetingRetrieveUpdateDestroyView.as_view(), name='meeting-detail'),
]
