from django.contrib import admin
from .models import Startup, Phase, Idea, Milestone, Meeting

@admin.register(Phase)
class PhaseAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    ordering = ('order',)

@admin.register(Startup)
class StartupAdmin(admin.ModelAdmin):
    list_display = ('name', 'founder', 'current_phase', 'created_at')
    list_filter = ('current_phase', 'created_at')
    search_fields = ('name', 'description', 'founder__username', 'founder__email')

@admin.register(Idea)
class IdeaAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'owner__username')

@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('title', 'startup', 'phase', 'due_date', 'completed')
    list_filter = ('completed', 'phase', 'due_date')
    search_fields = ('title', 'startup__name')

@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('title', 'startup', 'mentor', 'schedule_date')
    list_filter = ('schedule_date',)
    search_fields = ('title', 'startup__name', 'mentor__username')
