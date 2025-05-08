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
    
    # Get study statistics
    from rooms.models import StudySession, Room
    from django.db.models import Sum, Count, Avg
    from django.utils import timezone
    from datetime import timedelta
    
    # Calculate total hours and minutes studied
    total_minutes = user.profile.total_study_time
    hours_studied = total_minutes // 60
    minutes_studied = total_minutes % 60
    
    # Get recent study sessions (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_sessions = StudySession.objects.filter(
        user=user,
        start_time__gte=thirty_days_ago
    ).order_by('-start_time')
    
    # Get most active rooms
    room_stats = StudySession.objects.filter(user=user).values(
        'room__name', 'room__id', 'room__category'
    ).annotate(
        total_time=Sum('duration'),
        session_count=Count('id')
    ).order_by('-total_time')[:5]
    
    # Daily study time for the past 7 days
    seven_days_ago = timezone.now() - timedelta(days=7)
    daily_stats = []
    
    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        day_name = day.strftime('%A')
        day_start = timezone.make_aware(timezone.datetime(day.year, day.month, day.day))
        day_end = day_start + timedelta(days=1)
        
        day_sessions = StudySession.objects.filter(
            user=user,
            start_time__gte=day_start,
            start_time__lt=day_end
        )
        
        day_total = day_sessions.aggregate(total=Sum('duration'))['total'] or 0
        daily_stats.append({
            'day': day_name,
            'minutes': day_total
        })
    
    # Average study time per session
    avg_session_time = StudySession.objects.filter(
        user=user,
        duration__gt=0
    ).aggregate(avg=Avg('duration'))['avg'] or 0
    
    context = {
        'user': user,
        'hours_studied': hours_studied,
        'minutes_studied': minutes_studied,
        'recent_sessions': recent_sessions[:10],  # Last 10 sessions
        'room_stats': room_stats,
        'daily_stats': daily_stats,
        'avg_session_time': round(avg_session_time, 1)
    }
    
    return render(request, 'accounts/profile.html', context)

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