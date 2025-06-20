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
    followers = models.ManyToManyField(User, related_name='following', symmetrical=False, blank=True)

    def __str__(self):
        return f"{self.user.username}'s profile"
    
    @property
    def follower_count(self):
        return self.followers.count()

    @property
    def following_count(self):
        return self.user.following.count()

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    Profile.objects.get_or_create(user=instance)
    instance.profile.save()
