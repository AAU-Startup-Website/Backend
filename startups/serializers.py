from rest_framework import serializers
from .models import Startup, Idea, Phase, Milestone, Meeting
from users.serializers import UserSerializer
from startup_portal.serializers import StrictModelSerializer, validate_upload_file

PITCH_ALLOWED_EXTENSIONS = {'pdf', 'ppt', 'pptx', 'doc', 'docx'}
PITCH_ALLOWED_MIME = {
    'application/pdf',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}


class PhaseSerializer(StrictModelSerializer):
    class Meta:
        model = Phase
        fields = ['id', 'name', 'order']


class MilestoneSerializer(StrictModelSerializer):
    class Meta:
        model = Milestone
        fields = ['id', 'startup', 'phase', 'title', 'description', 'due_date', 'completed']


class StartupSerializer(StrictModelSerializer):
    founder_details = UserSerializer(source='founder', read_only=True)
    phase_details = PhaseSerializer(source='current_phase', read_only=True)

    class Meta:
        model = Startup
        fields = [
            'id', 'name', 'description', 'founder', 'founder_details',
            'created_at', 'current_phase', 'phase_details',
        ]
        read_only_fields = ['founder', 'created_at']

    def create(self, validated_data):
        validated_data['founder'] = self.context['request'].user
        return super().create(validated_data)


class IdeaSerializer(StrictModelSerializer):
    owner_details = UserSerializer(source='owner', read_only=True)

    class Meta:
        model = Idea
        fields = [
            'id', 'title', 'description', 'owner', 'owner_details', 'status',
            'created_at', 'startup',
            'problem_statement', 'target_audience', 'problem_scale',
            'existing_solutions', 'problem_urgency',
            'solution', 'unique_value_proposition', 'product_type',
            'technologies_used', 'development_stage', 'key_features',
            'market_size_estimation', 'target_market', 'market_trend',
            'competitive_landscape', 'customer_acquisition_strategy',
            'revenue_model', 'pricing_strategy',
            'team_vision', 'hiring_plan', 'team_size',
            'industry', 'business_stage', 'funding_requirements',
            'business_model', 'current_traction', 'key_challenges',
            'development_timeline', 'pitch_deck',
        ]
        read_only_fields = ['owner', 'created_at', 'status', 'startup']

    def validate_pitch_deck(self, value):
        return validate_upload_file(
            value,
            max_mb=10,
            allowed_extensions=PITCH_ALLOWED_EXTENSIONS,
            allowed_content_types=PITCH_ALLOWED_MIME,
        )

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        # Clients cannot set server-controlled fields
        validated_data.pop('status', None)
        validated_data.pop('startup', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('status', None)
        validated_data.pop('startup', None)
        validated_data.pop('owner', None)
        return super().update(instance, validated_data)


class MeetingSerializer(StrictModelSerializer):
    startup_details = StartupSerializer(source='startup', read_only=True)
    mentor_details = UserSerializer(source='mentor', read_only=True)

    class Meta:
        model = Meeting
        fields = [
            'id', 'startup', 'mentor', 'startup_details', 'mentor_details',
            'title', 'description', 'schedule_date', 'link',
        ]
        read_only_fields = ['schedule_date']  # server-generated via auto_now_add

    def validate_mentor(self, mentor):
        profile = getattr(mentor, 'profile', None)
        if profile and profile.role not in ('mentor', 'admin'):
            raise serializers.ValidationError('Selected user must have mentor (or admin) role.')
        return mentor

    def create(self, validated_data):
        # schedule_date is server-controlled; strip if client sends it
        validated_data.pop('schedule_date', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('schedule_date', None)
        return super().update(instance, validated_data)
