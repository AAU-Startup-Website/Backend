from rest_framework import viewsets, permissions, status, generics, exceptions
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Startup, Idea, Phase, Milestone, Meeting
from .serializers import StartupSerializer, IdeaSerializer, PhaseSerializer, MilestoneSerializer, MeetingSerializer


class StartupViewSet(viewsets.ModelViewSet):
    queryset = Startup.objects.all()
    serializer_class = StartupSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(founder=self.request.user)

class IdeaViewSet(viewsets.ModelViewSet):
    queryset = Idea.objects.all()
    serializer_class = IdeaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        idea = self.get_object()
        idea.status = 'approved'
        idea.save()
        return Response({'status': 'idea approved'})

class PhaseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Phase.objects.all()
    serializer_class = PhaseSerializer
    permission_classes = [permissions.AllowAny]

class MilestoneViewSet(viewsets.ModelViewSet):
    queryset = Milestone.objects.all()
    serializer_class = MilestoneSerializer
    permission_classes = [permissions.IsAuthenticated]
class MeetingListCreateView(generics.ListCreateAPIView):
    queryset = Meeting.objects.all()
    serializer_class = MeetingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # User sees meetings where they are the mentor OR the founder of the startup involved
        return Meeting.objects.filter(Q(mentor=user) | Q(startup__founder=user))

    def perform_create(self, serializer):
        # Ensure the creating user is the founder of the startup
        startup = serializer.validated_data['startup']
        if startup.founder != self.request.user:
             raise exceptions.PermissionDenied("Only the startup founder can book meetings.")
        serializer.save()

class MeetingRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Meeting.objects.all()
    serializer_class = MeetingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        # Check if user is the mentor OR the founder
        if obj.mentor != user and obj.startup.founder != user:
            raise exceptions.PermissionDenied("You do not have permission to view or edit this meeting.")
        return obj



