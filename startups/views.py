from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Startup, Idea, Phase, Milestone
from .serializers import StartupSerializer, IdeaSerializer, PhaseSerializer, MilestoneSerializer

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
