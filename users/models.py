from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    pass

class Profile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('mentor', 'Mentor'),
        ('admin', 'Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    skills = models.TextField(blank=True, help_text="Comma-separated skills")
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
