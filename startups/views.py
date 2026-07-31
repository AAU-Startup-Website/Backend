from rest_framework import viewsets, permissions, status, generics, exceptions, filters
from django.db import transaction
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Startup, Idea, Phase, Milestone, Meeting
from .serializers import (
    StartupSerializer, IdeaSerializer, PhaseSerializer,
    MilestoneSerializer, MeetingSerializer,
)
from .permissions import (
    IsIdeaOwnerOrPortalAdmin,
    IsStartupFounderOrPortalAdmin,
    IsMilestoneStartupMemberOrPortalAdmin,
    IsMeetingParticipant,
    CanUpdateMeeting,
)
from users.permissions import IsPortalAdmin, is_portal_admin

class StartupViewSet(viewsets.ModelViewSet):
    queryset = Startup.objects.select_related('founder', 'founder__profile', 'current_phase').all()
    serializer_class = StartupSerializer
    permission_classes = [IsStartupFounderOrPortalAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        serializer.save(founder=self.request.user)


class IdeaViewSet(viewsets.ModelViewSet):
    queryset = Idea.objects.select_related('owner', 'owner__profile', 'startup').all()
    serializer_class = IdeaSerializer
    permission_classes = [permissions.IsAuthenticated, IsIdeaOwnerOrPortalAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'industry']
    ordering_fields = ['created_at', 'status', 'title']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_portal_admin(user):
            return qs
        return qs.filter(owner=user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsPortalAdmin])
    def approve(self, request, pk=None):
        """
        Admin-only idea approval (atomic):
        - set status approved
        - create startup with founder = idea.owner
        - link startup back to idea
        - prevent duplicate approval
        """
        with transaction.atomic():
            try:
                idea = Idea.objects.select_for_update().select_related('startup', 'owner').get(pk=pk)
            except Idea.DoesNotExist:
                return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

            if idea.status == 'approved' and idea.startup_id:
                return Response(
                    {
                        'detail': 'Idea already approved.',
                        'startup_id': idea.startup_id,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if idea.status == 'rejected':
                return Response(
                    {'detail': 'Rejected ideas cannot be approved.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            idea.status = 'approved'
            if idea.startup_id is None:
                startup = Startup.objects.create(
                    name=idea.title,
                    description=idea.description,
                    founder=idea.owner,
                )
                idea.startup = startup
            idea.save(update_fields=['status', 'startup'])

        return Response({
            'status': 'idea approved',
            'startup_id': idea.startup_id,
        })

    @action(detail=True, methods=['post'], permission_classes=[IsPortalAdmin])
    def reject(self, request, pk=None):
        with transaction.atomic():
            idea = self.get_object()
            if idea.status == 'approved':
                return Response(
                    {'detail': 'Approved ideas cannot be rejected.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            idea.status = 'rejected'
            idea.save(update_fields=['status'])
        return Response({'status': 'idea rejected'})


class PhaseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Phase.objects.all()
    serializer_class = PhaseSerializer
    permission_classes = [permissions.AllowAny]


class MilestoneViewSet(viewsets.ModelViewSet):
    queryset = Milestone.objects.select_related('startup', 'phase', 'startup__founder').all()
    serializer_class = MilestoneSerializer
    permission_classes = [permissions.IsAuthenticated, IsMilestoneStartupMemberOrPortalAdmin]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['due_date', 'completed']
    ordering = ['due_date']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_portal_admin(user):
            return qs
        return qs.filter(startup__founder=user)


class MeetingListCreateView(generics.ListCreateAPIView):
    serializer_class = MeetingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['schedule_date', 'title']
    ordering = ['-schedule_date']

    def get_queryset(self):
        user = self.request.user
        qs = Meeting.objects.select_related(
            'startup', 'startup__founder', 'mentor', 'mentor__profile'
        )
        if is_portal_admin(user):
            return qs.all()
        # Mentor visibility OR founder visibility
        return qs.filter(Q(mentor=user) | Q(startup__founder=user))

    def perform_create(self, serializer):
        startup = serializer.validated_data['startup']
        if startup.founder != self.request.user and not is_portal_admin(self.request.user):
            raise exceptions.PermissionDenied('Only the startup founder can book meetings.')
        # schedule_date is server-generated (model auto_now_add)
        serializer.save()


class MeetingRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MeetingSerializer
    permission_classes = [permissions.IsAuthenticated, IsMeetingParticipant, CanUpdateMeeting]

    def get_queryset(self):
        return Meeting.objects.select_related(
            'startup', 'startup__founder', 'mentor', 'mentor__profile'
        )

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if is_portal_admin(user):
            return obj
        if obj.mentor != user and obj.startup.founder != user:
            raise exceptions.PermissionDenied(
                'You do not have permission to view or edit this meeting.'
            )
        return obj
