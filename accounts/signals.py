from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.utils import timezone
from datetime import timedelta
from accounts.models import Profile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

@receiver(user_logged_in)
def handle_user_login_streak(sender, request, user, **kwargs):
    today = timezone.now().date()
    profile = user.profile # Assuming user.profile is already created by post_save signal

    if profile.last_login_date:
        yesterday = today - timedelta(days=1)
        if profile.last_login_date == yesterday:
            profile.streak += 1
        elif profile.last_login_date != today: # Only reset if last login wasn't also today
            profile.streak = 1 # Reset to 1 if they missed a day
    else:
        # First login or first time tracking streak
        profile.streak = 1

    profile.last_login_date = today
    profile.save()