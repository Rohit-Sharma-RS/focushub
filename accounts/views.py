# accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
import datetime
from .forms import SignupForm, CustomLoginForm
from django.db.models import Count, Sum, Avg
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from rooms.models import StudySession
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

def signup(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                messages.success(request, f'Welcome {user.username}! Your account has been created successfully.')
                return redirect('home')
            except Exception as e:
                messages.error(request, 'An error occurred while creating your account. Please try again.')
                # Log the error for debugging
                print(f"Signup error: {e}")
        else:
            # Form has validation errors - they will be displayed in the template
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SignupForm()
    
    return render(request, 'accounts/signup.html', {'form': form})


class CustomLoginView(LoginView):
    form_class = CustomLoginForm
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        messages.success(self.request, f'Welcome back, {form.get_user().username}!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        # Add a general error message for invalid login
        messages.error(self.request, 'Invalid login credentials. Please check your username and password.')
        return super().form_invalid(form)


# Alternative function-based login view if you prefer
def custom_login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            # Form validation errors will be displayed automatically
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomLoginForm()
    
    return render(request, 'registration/login.html', {'form': form})


@login_required
def profile(request):
    user = request.user

    # Get study statistics
    from rooms.models import StudySession, Room

    # total_study_time is now stored in seconds
    total_seconds = user.profile.total_study_time or 0
    hours_studied = total_seconds // 3600
    minutes_studied = (total_seconds % 3600) // 60

    # Get recent study sessions (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_sessions = StudySession.objects.filter(
        user=user,
        start_time__gte=thirty_days_ago
    ).order_by('-start_time')[:10]

    # Get most active rooms
    room_stats = StudySession.objects.filter(user=user).values(
        'user__username', 'room__name', 'room__id', 'room__category'
    ).annotate(
        total_time_seconds=Sum('duration'),
        session_count=Count('id')
    ).order_by('-total_time_seconds')[:5]

    # Convert room stats total time to hours/minutes for display
    for stat in room_stats:
        total_seconds_stat = stat['total_time_seconds'] or 0
        stat['hours'] = total_seconds_stat // 3600
        stat['minutes'] = (total_seconds_stat % 3600) // 60

    # Daily study time for the past 7 days
    seven_days_ago = timezone.now() - timedelta(days=7)
    daily_stats = []
    daily_session_counts = []

    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        day_start = timezone.make_aware(timezone.datetime(day.year, day.month, day.day))
        day_end = day_start + timedelta(days=1)

        day_total_seconds = StudySession.objects.filter(
            user=user,
            start_time__gte=day_start,
            start_time__lt=day_end
        ).aggregate(total=Sum('duration'))['total'] or 0

        sessions_on_day_count = StudySession.objects.filter(
             user=user,
             start_time__gte=day_start,
             start_time__lt=day_end
         ).count()

        daily_stats.append({
            'day': day.strftime('%A'),
            'minutes': day_total_seconds // 60
        })
        daily_session_counts.append(sessions_on_day_count)

    # Average study time per session
    avg_session_time_seconds = StudySession.objects.filter(
        user=user,
        duration__gt=0
    ).aggregate(avg=Avg('duration'))['avg'] or 0

    avg_session_time_minutes = round(avg_session_time_seconds / 60, 1)

    # Category study time
    category_data = StudySession.objects.filter(user=user).values(
        'room__category'
    ).annotate(
        total_duration_seconds=Sum('duration')
    ).order_by('-total_duration_seconds')

    category_labels = [item['room__category'] for item in category_data if item['room__category']]
    category_values = [item['total_duration_seconds'] // 60 for item in category_data if item['room__category']]

    # Time of day study time
    time_slots = {
        'Morning': (datetime.time(6, 0), datetime.time(11, 59, 59)),
        'Afternoon': (datetime.time(12, 0), datetime.time(16, 59, 59)),
        'Evening': (datetime.time(17, 0), datetime.time(20, 59, 59)),
        'Night': (datetime.time(21, 0), datetime.time(23, 59, 59)),
        'Late Night': (datetime.time(0, 0), datetime.time(2, 59, 59)),
        'Early Morning': (datetime.time(3, 0), datetime.time(5, 59, 59)),
    }

    time_of_day_labels = list(time_slots.keys())
    time_of_day_values_seconds = [0] * len(time_of_day_labels)

    user_sessions = StudySession.objects.filter(user=user)

    for session in user_sessions:
        if session.start_time:
            session_time = timezone.localtime(session.start_time).time()
            session_duration_seconds = session.duration or 0

            for i, (slot_name, (start_slot, end_slot)) in enumerate(time_slots.items()):
                 if start_slot <= end_slot:
                     if start_slot <= session_time <= end_slot:
                         time_of_day_values_seconds[i] += session_duration_seconds
                         break
                 else:
                     if session_time >= start_slot or session_time <= end_slot:
                         time_of_day_values_seconds[i] += session_duration_seconds
                         break

    time_of_day_values_minutes = [s // 60 for s in time_of_day_values_seconds]

    # Study calendar data (last 90 days)
    ninety_days_ago = timezone.now() - timedelta(days=90)
    calendar_sessions = StudySession.objects.filter(
        user=user,
        start_time__gte=ninety_days_ago
    ).values(
        'start_time__date'
    ).annotate(
        total_duration_on_day_seconds=Sum('duration')
    ).order_by('start_time__date')

    study_calendar_data = []
    sessions_by_date_seconds = {
        item['start_time__date'].isoformat(): item['total_duration_on_day_seconds']
        for item in calendar_sessions
    }

    for i in range(90):
        day_date = (ninety_days_ago + timedelta(days=i)).date()
        duration_seconds = sessions_by_date_seconds.get(day_date.isoformat(), 0)

        scaled_value = 0
        if duration_seconds > 120 * 60:
            scaled_value = 4
        elif duration_seconds > 60 * 60:
            scaled_value = 3
        elif duration_seconds > 30 * 60:
            scaled_value = 2
        elif duration_seconds > 0:
            scaled_value = 1

        study_calendar_data.append({
            "date": day_date.isoformat(),
            "value": scaled_value
        })

    context = {
        'user': user,
        'hours_studied': hours_studied,
        'minutes_studied': minutes_studied,
        'recent_sessions': recent_sessions,
        'room_stats': room_stats,
        'daily_stats': daily_stats,
        'daily_session_counts': daily_session_counts,
        'avg_session_time': avg_session_time_minutes,
        'category_labels': category_labels,
        'category_values': category_values,
        'time_of_day_labels': time_of_day_labels,
        'time_of_day_values': time_of_day_values_minutes,
        'study_calendar_data': study_calendar_data,
        'follower_count': user.profile.follower_count,
        'following_count': user.profile.following_count,
    }

    return render(request, 'accounts/profile.html', context)

@login_required
def view_profile(request, username):
    """
    New view to display the profile of any user.
    """
    profile_user = get_object_or_404(User, username=username)

    # Redirect to the main profile page if a user tries to view their own profile via this URL.
    if request.user == profile_user:
        return redirect('profile')

    # Get study statistics for the user whose profile is being viewed.
    total_seconds = profile_user.profile.total_study_time or 0
    hours_studied = total_seconds // 3600
    minutes_studied = (total_seconds % 3600) // 60
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_sessions = StudySession.objects.filter(user=profile_user, start_time__gte=thirty_days_ago).order_by('-start_time')[:10]

    # Check if the currently logged-in user is following the user they are viewing.
    is_following = request.user.following.filter(user=profile_user).exists()

    context = {
        'profile_user': profile_user,
        'is_following': is_following,
        'follower_count': profile_user.profile.follower_count,
        'following_count': profile_user.profile.following_count,
        'hours_studied': hours_studied,
        'minutes_studied': minutes_studied,
        'recent_sessions': recent_sessions,
    }
    
    return render(request, 'accounts/view_profile.html', context)

@login_required
def toggle_follow(request, username):
    """
    New view to handle the logic of following and unfollowing a user.
    """
    if request.method == 'POST':
        user_to_toggle = get_object_or_404(User, username=username)

        # Prevent users from following themselves.
        if user_to_toggle == request.user:
            messages.error(request, "You cannot follow yourself.")
            return redirect('view_profile', username=username)

        # Check if the current user is already following, then toggle.
        if user_to_toggle.profile.followers.filter(id=request.user.id).exists():
            # Unfollow the user
            user_to_toggle.profile.followers.remove(request.user)
            messages.info(request, f"You have unfollowed {username}.")
        else:
            # Follow the user
            user_to_toggle.profile.followers.add(request.user)
            messages.success(request, f"You are now following {username}.")
        
        return redirect('view_profile', username=username)
    else:
        # Redirect if the request is not POST.
        return redirect('view_profile', username=username)


@login_required
def update_streak(request):
    user = request.user
    today = timezone.now().date()

    last_login_date = user.profile.last_login_date
    if isinstance(last_login_date, datetime.datetime):
        last_login_date = last_login_date.date()

    last_study_session = user.studysession_set.order_by('-start_time').first()
    last_study_date = last_study_session.start_time.date() if last_study_session and last_study_session.start_time else None

    is_consecutive_day = False
    if last_study_date:
        yesterday = today - timedelta(days=1)
        if last_study_date == yesterday:
            is_consecutive_day = True
        elif last_study_date == today:
             pass
        else:
            if StudySession.objects.filter(user=user, start_time__date=today).exists():
                 user.profile.streak = 1
                 user.profile.save()
                 return redirect('profile')

    if is_consecutive_day or (last_study_date is None and StudySession.objects.filter(user=user, start_time__date=today).exists()):
         user.profile.streak = (user.profile.streak or 0) + 1
         user.profile.save()

    return redirect('profile')