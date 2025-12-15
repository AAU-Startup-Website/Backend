from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['bio', 'role', 'skills']

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=False)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'profile']

    def create(self, validated_data):
        profile_data = validated_data.pop('profile', {})
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        
        if profile_data:
            # Profile might be created by signal, check first
            if not hasattr(user, 'profile'):
                Profile.objects.create(user=user, **profile_data)
            else:
                for attr, value in profile_data.items():
                    setattr(user.profile, attr, value)
                user.profile.save()
        elif not hasattr(user, 'profile'):
             Profile.objects.create(user=user)
             
        return user

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', {})
        password = validated_data.pop('password', None)
        
        if password:
            instance.set_password(password)
            instance.save()
            
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if profile_data:
            if hasattr(instance, 'profile'):
                for attr, value in profile_data.items():
                    setattr(instance.profile, attr, value)
                instance.profile.save()
            else:
                Profile.objects.create(user=instance, **profile_data)
            
        return instance
