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

    problem_statement = models.TextField(blank=True, default='')
    target_audience = models.TextField(blank=True, default='')
    problem_scale = models.CharField(max_length=50, blank=True, default='')
    existing_solutions = models.TextField(blank=True, default='')
    problem_urgency = models.CharField(max_length=50, blank=True, default='')

    solution = models.TextField(blank=True, default='')
    unique_value_proposition = models.TextField(blank=True, default='')
    product_type = models.CharField(max_length=50, blank=True, default='')
    technologies_used = models.TextField(blank=True, default='')
    development_stage = models.CharField(max_length=50, blank=True, default='')
    key_features = models.TextField(blank=True, default='')

    market_size_estimation = models.TextField(blank=True, default='')
    target_market = models.TextField(blank=True, default='')
    market_trend = models.TextField(blank=True, default='')
    competitive_landscape = models.TextField(blank=True, default='')
    customer_acquisition_strategy = models.TextField(blank=True, default='')
    revenue_model = models.CharField(max_length=50, blank=True, default='')
    pricing_strategy = models.CharField(max_length=50, blank=True, default='')

    team_vision = models.TextField(blank=True, default='')
    hiring_plan = models.TextField(blank=True, default='')
    team_size = models.IntegerField(null=True, blank=True) # For future upgrade it to accept the profile of users
    
    industry = models.CharField(max_length=150, blank=True, default='')
    business_stage = models.CharField(max_length=50, blank=True, default='')
    funding_requirements = models.TextField(blank=True, default='')
    business_model = models.TextField(blank=True, default='')
    current_traction = models.TextField(blank=True, default='')
    key_challenges = models.TextField(blank=True, default='')
    development_timeline = models.TextField(blank=True, default='')
    
    pitch_deck = models.FileField(upload_to='idea_pitches/', null=True, blank=True)



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
class Meeting(models.Model):
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='meetings')
    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='meetings')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    schedule_date = models.DateTimeField(auto_now_add=True)
    link = models.URLField(blank=True)
