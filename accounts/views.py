from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
import datetime
from .forms import SignupForm

def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = SignupForm()
    return render(request, 'accounts/signup.html', {'form': form})

@login_required
def profile(request):
    user = request.user
    return render(request, 'accounts/profile.html', {'user': user})

@login_required
def update_streak(request):
    user = request.user
    today = timezone.now().date()
    
    if user.profile.last_login_date:
        yesterday = today - timedelta(days=1)
        if user.profile.last_login_date == yesterday:
            user.profile.streak += 1
        elif user.profile.last_login_date != today:
            user.profile.streak = 1
    else:
        user.profile.streak = 1
        
    user.profile.last_login_date = today
    user.profile.save()
    
    return redirect('profile')