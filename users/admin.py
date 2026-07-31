from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fk_name = 'user'
    fields = ('bio', 'role', 'skills', 'failed_login_attempts', 'lockout_until')
    readonly_fields = ('failed_login_attempts', 'lockout_until')


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    inlines = [ProfileInline]
    list_display = ('username', 'email', 'is_staff', 'is_superuser', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'failed_login_attempts', 'lockout_until')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'skills')
