from django.db import models
from django.conf import settings

class Phase(models.Model):
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name

class Startup(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    founder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='startups')
    created_at = models.DateTimeField(auto_now_add=True)
    current_phase = models.ForeignKey(Phase, on_delete=models.SET_NULL, null=True, blank=True, related_name='startups')

    def __str__(self):
        return self.name

class Idea(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ideas')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Optional: Link to startup if approved
    startup = models.OneToOneField(Startup, on_delete=models.SET_NULL, null=True, blank=True, related_name='idea')

    def __str__(self):
        return self.title

class Milestone(models.Model):
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='milestones')
    phase = models.ForeignKey(Phase, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.startup.name} - {self.title}"
