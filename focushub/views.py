from django.shortcuts import render
from django.contrib.auth.models import User
from rooms.models import Room, StudySession
from django.db.models import Sum, Count
from django.utils import timezone

def home(request):
    # Get platform stats
    total_users = User.objects.count()
    total_rooms = Room.objects.count()
    
    # Calculate total hours focused
    total_minutes = StudySession.objects.aggregate(
        total=Sum('duration')
    )['total'] or 0
    total_hours = total_minutes // 60
    
    # Get count of unique subject categories
    total_subjects = Room.objects.values('category').distinct().count()
    
    # Get active rooms with user count
    available_rooms = Room.objects.annotate(
        active_users=Count('members')
    ).filter(
        active_users__gt=0
    ).order_by('-active_users')[:5]  # Top 5 most active rooms
    
    # Assign colors based on category (for visual distinction)
    color_mapping = {
        'Mathematics': 'blue',
        'Science': 'green',
        'Language': 'red',
        'Computer Science': 'purple',
        'Arts': 'pink',
        'History': 'amber',
        'Business': 'emerald',
    }
    
    # Add color attribute to rooms
    for room in available_rooms:
        room.color = color_mapping.get(room.category, 'indigo')
    
    context = {
        'total_users': total_users,
        'total_rooms': total_rooms,
        'total_hours': total_hours//60,
        'total_subjects': total_subjects,
        'available_rooms': available_rooms,
    }
    
    return render(request, 'home.html', context)