from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Profile
from startup_portal.serializers import StrictModelSerializer, StrictSerializerMixin

User = get_user_model()


class ProfileSerializer(StrictModelSerializer):
    class Meta:
        model = Profile
        fields = ['bio', 'role', 'skills']
        read_only_fields = []  # role writability controlled in parent serializers


class UserSerializer(StrictModelSerializer):
    profile = ProfileSerializer(required=False)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'profile']
        read_only_fields = ['id']

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_profile(self, profile_data):
        """
        Privilege escalation prevention:
        - Registration may set student/mentor/admin profile.role
        - profile.role NEVER sets is_staff / is_superuser (enforced in create/update)
        - Non-staff users cannot change their own role on update
        """
        request = self.context.get('request')
        role = profile_data.get('role')

        if self.instance is not None and role is not None:
            # Updating existing user
            if request and request.user.is_authenticated:
                if not (request.user.is_staff or request.user.is_superuser):
                    # Strip role changes from non-staff self-service updates
                    current = getattr(self.instance, 'profile', None)
                    current_role = current.role if current else 'student'
                    if role != current_role:
                        raise serializers.ValidationError(
                            {'role': 'You cannot change your own role.'}
                        )
        return profile_data

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', {})
        password = validated_data.pop('password')

        # Never grant Django admin privileges from profile/API registration
        validated_data.pop('is_staff', None)
        validated_data.pop('is_superuser', None)

        user = User.objects.create_user(password=password, **validated_data)
        # create_user never sets staff; reinforce
        if user.is_staff or user.is_superuser:
            user.is_staff = False
            user.is_superuser = False
            user.save(update_fields=['is_staff', 'is_superuser'])

        role = profile_data.get('role', 'student')
        if role not in dict(Profile.ROLE_CHOICES):
            raise serializers.ValidationError({'profile': {'role': 'Invalid role.'}})

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.bio = profile_data.get('bio', profile.bio)
        profile.skills = profile_data.get('skills', profile.skills)
        profile.role = role
        profile.save()

        return user

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        password = validated_data.pop('password', None)

        # Block privilege escalation via API
        validated_data.pop('is_staff', None)
        validated_data.pop('is_superuser', None)

        if password:
            instance.set_password(password)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if profile_data:
            profile, _ = Profile.objects.get_or_create(user=instance)
            request = self.context.get('request')
            can_set_role = request and request.user.is_authenticated and (
                request.user.is_staff or request.user.is_superuser
            )
            for attr, value in profile_data.items():
                if attr == 'role' and not can_set_role:
                    continue
                setattr(profile, attr, value)
            profile.save()

        return instance


class PasswordResetSerializer(StrictSerializerMixin, serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # Do not reveal whether the email exists (enumeration hardening).
        # Existence check happens silently in the view.
        return value


class PasswordResetConfirmSerializer(StrictSerializerMixin, serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=8)
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate_new_password(self, value):
        validate_password(value)
        return value
