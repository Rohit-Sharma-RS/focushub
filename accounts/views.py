from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
import datetime
from .forms import SignupForm
from django.db.models import Count

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

    total_seconds = user.profile.total_study_time
    total_minutes = total_seconds // 60
    hours_studied   = total_minutes // 60
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
    daily_session_counts = []

    
    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        # day_name = day.strftime('%A')
        day_start = timezone.make_aware(timezone.datetime(day.year, day.month, day.day))
        day_end = day_start + timedelta(days=1)

        sessions_on_day = StudySession.objects.filter(
            user=user,
            start_time__gte=day_start,
            start_time__lt=day_end
        ).count()

        day_sessions = StudySession.objects.filter(
            user=user,
            start_time__gte=day_start,
            start_time__lt=day_end
        )
        day_name = day.strftime('%A')
        day_total = day_sessions.aggregate(total=Sum('duration'))['total'] or 0
        daily_stats.append({
            'day': day_name,
            'minutes': day_total
        })
        daily_session_counts.append(sessions_on_day)

    
    # Average study time per session
    avg_session_time = StudySession.objects.filter(
        user=user,
        duration__gt=0
    ).aggregate(avg=Avg('duration'))['avg'] or 0
    
    category_data = StudySession.objects.filter(user=user).values(
        'room__category' # Group by room category
    ).annotate(
        total_duration=Sum('duration') # Sum of duration for each category
    ).order_by('-total_duration')

    category_labels = [item['room__category'] for item in category_data if item['room__category']]
    category_values = [item['total_duration'] for item in category_data if item['room__category']]

    time_slots = {
        'Morning': (datetime.time(6, 0), datetime.time(11, 59, 59)),
        'Afternoon': (datetime.time(12, 0), datetime.time(16, 59, 59)),
        'Evening': (datetime.time(17, 0), datetime.time(20, 59, 59)),
        'Night': (datetime.time(21, 0), datetime.time(23, 59, 59)),
        'Late Night': (datetime.time(0, 0), datetime.time(2, 59, 59)), # Covers past midnight
        'Early Morning': (datetime.time(3, 0), datetime.time(5, 59, 59)),
    }
    
    time_of_day_labels = list(time_slots.keys())
    time_of_day_values = [0] * len(time_of_day_labels)
    
    user_sessions = StudySession.objects.filter(user=user)
    
    for session in user_sessions:
        # Ensure start_time is a datetime object and timezone aware if necessary
        session_time = timezone.localtime(session.start_time).time() # Convert to local time
        for i, (slot_name, (start_slot, end_slot)) in enumerate(time_slots.items()):
            if start_slot <= session_time <= end_slot:
                time_of_day_values[i] += session.duration # Summing duration
                break
            # Handle cases spanning midnight if necessary, e.g. Late Night into Early Morning
            # For simplicity, this example assumes session start time determines the slot.
    ninety_days_ago = timezone.now() - timedelta(days=90)
    calendar_sessions = StudySession.objects.filter(
        user=user,
        start_time__gte=ninety_days_ago
    ).values(
        'start_time__date' # Group by date
    ).annotate(
        total_duration_on_day=Sum('duration')
    ).order_by('start_time__date')

    # Format for D3 calendar: [{date: "YYYY-MM-DD", value: study_metric}, ...]
    # 'value' could be number of sessions, total minutes, or a scaled intensity (0-4)
    # For this example, let's use total minutes and scale it later in JS or just use minutes.
    study_calendar_data = []
    # Create a dictionary for quick lookup
    sessions_by_date = {
        item['start_time__date'].isoformat(): item['total_duration_on_day'] 
        for item in calendar_sessions
    }

    for i in range(90): # Generate entries for all days in the last 90 days
        day_date = (ninety_days_ago + timedelta(days=i)).date()
        duration = sessions_by_date.get(day_date.isoformat(), 0) # Get duration or 0 if no session
        
        # Simple scaling for the 0-4 value example the D3 chart expects
        # You might want a more sophisticated scaling
        scaled_value = 0
        if duration > 120: # Over 2 hours
            scaled_value = 4
        elif duration > 60: # Over 1 hour
            scaled_value = 3
        elif duration > 30: # Over 30 mins
            scaled_value = 2
        elif duration > 0: # Any study
            scaled_value = 1
            
        study_calendar_data.append({
            "date": day_date.isoformat(),
            "value": scaled_value # Or pass raw duration and handle scaling in JS
        })

    context = {
        'user': user,
        'hours_studied': hours_studied,
        'minutes_studied': minutes_studied,
        'recent_sessions': recent_sessions[:10],  # Last 10 sessions
        'room_stats': room_stats,
        'daily_stats': daily_stats,
        'daily_session_counts': daily_session_counts,
        'avg_session_time': round(avg_session_time, 1),
        'category_labels': category_labels,
        'category_values': category_values,
        'time_of_day_labels': time_of_day_labels,
        'time_of_day_values': time_of_day_values,
        'study_calendar_data': study_calendar_data,
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