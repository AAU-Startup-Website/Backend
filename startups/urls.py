from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StartupViewSet, IdeaViewSet, PhaseViewSet, MilestoneViewSet

router = DefaultRouter()
router.register(r'startups', StartupViewSet)
router.register(r'ideas', IdeaViewSet)
router.register(r'phases', PhaseViewSet)
router.register(r'milestones', MilestoneViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
