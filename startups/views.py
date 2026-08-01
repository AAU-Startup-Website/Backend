from rest_framework import viewsets, permissions, status, generics, exceptions
from django.db import transaction
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Startup, Idea, Phase, Milestone, Meeting
from .serializers import StartupSerializer, IdeaSerializer, PhaseSerializer, MilestoneSerializer, MeetingSerializer
from audit.utils import log_action


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

        if idea.status == 'approved':
            # Idempotency guard: re-approving an already-approved idea is a
            # documented no-op, not a silent re-approval that could re-run
            # side effects or mask a stale client state.
            return Response(
                {
                    'status': 'idea already approved',
                    'startup_id': idea.startup.id if idea.startup else None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            idea.status = 'approved'
            idea.save()

            if not hasattr(idea, 'startup') or idea.startup is None:
                startup = Startup.objects.create(
                    name=idea.title,
                    description=idea.description,
                    founder=idea.owner
                )
                idea.startup = startup
                idea.save()

        log_action(
            request.user,
            action='idea.approve',
            target_type='Idea',
            target_id=idea.id,
            idea_title=idea.title,
            startup_id=idea.startup.id,
        )
        return Response({'status': 'idea approved', 'startup_id': idea.startup.id})

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
    serializer_class = MeetingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Scoping the queryset itself (rather than fetching unfiltered and
        # manually raising PermissionDenied) means an out-of-scope meeting ID
        # returns a plain 404 — identical to a nonexistent ID — instead of a
        # 403 that confirms the meeting exists but isn't visible to this user.
        user = self.request.user
        return Meeting.objects.filter(Q(mentor=user) | Q(startup__founder=user))



