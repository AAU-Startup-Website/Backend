from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import FileExtensionValidator
from rest_framework import serializers
from .models import ALLOWED_PITCH_DECK_EXTENSIONS, Startup, Idea, Phase, Milestone, Meeting
from .validators import validate_file_size
from users.serializers import UserSerializer

class PhaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Phase
        fields = '__all__'

class MilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Milestone
        fields = '__all__'

class StartupSerializer(serializers.ModelSerializer):
    founder_details = UserSerializer(source='founder', read_only=True)
    phase_details = PhaseSerializer(source='current_phase', read_only=True)
    
    class Meta:
        model = Startup
        fields = ['id', 'name', 'description', 'founder', 'founder_details', 'created_at', 'current_phase', 'phase_details']
        read_only_fields = ['founder', 'created_at']

    def create(self, validated_data):
        validated_data['founder'] = self.context['request'].user
        return super().create(validated_data)

class IdeaSerializer(serializers.ModelSerializer):
    owner_details = UserSerializer(source='owner', read_only=True)
    
    class Meta:
        model = Idea
        fields = '__all__'
        read_only_fields = ['owner', 'created_at', 'status', 'startup']

    def validate_pitch_deck(self, value):
        if value in (None, ''):
            return value
        extension_validator = FileExtensionValidator(allowed_extensions=ALLOWED_PITCH_DECK_EXTENSIONS)
        try:
            extension_validator(value)
            validate_file_size(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)
class MeetingSerializer(serializers.ModelSerializer):
    startup_details = StartupSerializer(source='startup', read_only=True)
    mentor_details = UserSerializer(source='mentor', read_only=True)

    class Meta:
        model = Meeting
        fields = ['id', 'startup', 'mentor', 'startup_details', 'mentor_details', 'title', 'description', 'schedule_date', 'link']