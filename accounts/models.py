from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.utils import timezone
from datetime import timedelta

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    streak = models.IntegerField(default=0)
    last_login_date = models.DateField(null=True, blank=True)
    total_study_time = models.IntegerField(default=0)  # in minutes
    
    def __str__(self):
        return f"{self.user.username}'s profile"

