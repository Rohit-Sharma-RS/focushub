from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.db.models import Sum
from .models import Room, Message, StudySession
from ai.sentiment import analyze_sentiment
from ai.groq_integration import summarize_chat, answer_question
import json

@login_required
def room_list(request):
    rooms = Room.objects.all()
    user_rooms = request.user.rooms_joined.all()
    return render(request, 'rooms/room_list.html', {'rooms': rooms, 'user_rooms': user_rooms})

@login_required
def create_room(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        category = request.POST.get('category', 'General')
        
        room = Room.objects.create(
            name=name,
            description=description,
            created_by=request.user,
            category=category
        )
        room.members.add(request.user)
        return redirect('room_detail', room_id=room.id)
    
    return render(request, 'rooms/create_room.html')

@login_required
def room_detail(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    messages = room.messages.order_by('timestamp')[:100]
    
    if request.user not in room.members.all():
        room.members.add(request.user)
    
    # Start a study session
    StudySession.objects.create(user=request.user, room=room)
    
    # Get raw leaderboard totals (in minutes)
    leaderboard_raw = StudySession.objects.filter(room=room) \
        .values('user__username') \
        .annotate(total_time=Sum('duration')) \
        .order_by('-total_time')[:5]

    # Convert minutes → hours/minutes
    leaderboard = []
    for entry in leaderboard_raw:
        total_minutes = entry['total_time'] or 0
        hours = total_minutes // 60
        minutes = total_minutes % 60
        leaderboard.append({
            'username': entry['user__username'],
            'hours': hours,
            'minutes': minutes,
        })
    
    # Get recommended rooms
    recommended_rooms = get_recommended_rooms(room)
    
    return render(request, 'rooms/room_detail.html', {
        'room': room, 
        'messages': messages,
        'leaderboard': leaderboard,
        'recommended_rooms': recommended_rooms
    })

@login_required
def leave_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    
    # End active study session
    active_session = StudySession.objects.filter(
        user=request.user,
        room=room,
        end_time__isnull=True
    ).first()
    
    if active_session:
        active_session.end_time = timezone.now()
        duration = (active_session.end_time - active_session.start_time).total_seconds() / 60
        active_session.duration = int(duration)
        active_session.save()
        
        # Update total study time in user profile
        request.user.profile.total_study_time += active_session.duration
        request.user.profile.save()
    
    if request.user in room.members.all():
        room.members.remove(request.user)
    
    return redirect('room_list')

@login_required
def update_timer(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        duration = data.get('duration')
        room_id = data.get('room_id')
        
        room = get_object_or_404(Room, id=room_id)
        
        # Update the most recent study session
        session = StudySession.objects.filter(
            user=request.user,
            room=room,
            end_time__isnull=True
        ).first()
        
        if session:
            session.duration = duration
            session.save()
        
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def summarize_room(request, room_id):
    """Generate a summary of recent room messages using Groq API"""
    if request.method == 'GET':
        room = get_object_or_404(Room, id=room_id)
        messages = room.messages.order_by('-timestamp')[:50]  # Last 50 messages
        
        # If no messages, return error
        if not messages:
            return JsonResponse({'summary': 'No messages to summarize'})
        
        # Format messages for summarization
        message_texts = [f"{msg.user.username}: {msg.content}" for msg in messages]
        message_texts.reverse()  # Put in chronological order
        
        # Get summary from Groq API
        summary = summarize_chat(message_texts)
        
        # Store summary in session for later use when asking questions
        request.session[f'room_{room_id}_summary'] = summary
        
        return JsonResponse({'summary': summary})
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@login_required
def ask_about_summary(request, room_id):
    """Answer questions about a room summary using Groq API"""
    if request.method == 'POST':
        data = json.loads(request.body)
        question = data.get('question')
        
        # Retrieve stored summary
        summary = request.session.get(f'room_{room_id}_summary')
        if not summary:
            return JsonResponse({'error': 'No summary available. Please generate a summary first.'}, status=400)
        
        # Get answer from Groq API
        answer = answer_question(summary, question)
        
        return JsonResponse({'answer': answer})
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

def get_recommended_rooms(current_room):
    """Simple room recommendation system based on category and common members"""
    
    # Get rooms with the same category
    category_rooms = Room.objects.filter(
        category=current_room.category
    ).exclude(id=current_room.id)
    
    # Get rooms with common members
    member_ids = current_room.members.values_list('id', flat=True)
    common_member_rooms = Room.objects.filter(
        members__in=member_ids
    ).exclude(id=current_room.id).distinct()
    
    # Combine and deduplicate
    recommended = list(category_rooms) + list(common_member_rooms)
    unique_rooms = list({room.id: room for room in recommended}.values())
    
    return unique_rooms[:3]  # Return top 3