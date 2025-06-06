from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.db.models import Sum
from .models import Room, Message, StudySession
from ai.sentiment import analyze_sentiment # Assuming these are needed elsewhere
from ai.groq_integration import summarize_chat, answer_question # Assuming these are needed elsewhere
import json
import logging

logger = logging.getLogger(__name__)

@login_required
def room_list(request):
    rooms = Room.objects.all()
    user_rooms = request.user.rooms_joined.all()

    # Handle room deletion (admin only)
    if request.method == 'POST' and request.user.is_staff:
        room_id = request.POST.get('room_id')
        if room_id:
            room = get_object_or_404(Room, id=room_id)
            room.delete()
            return redirect('room_list')

    return render(request, 'rooms/room_list.html', {
        'rooms': rooms,
        'user_rooms': user_rooms,
    })

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

    # Do NOT create a StudySession here. Session starts with the timer.

    # Get leaderboard totals (in seconds)
    # Sum 'duration' which will now store seconds
    leaderboard_raw = StudySession.objects.filter(room=room) \
        .values('user__username') \
        .annotate(total_time_seconds=Sum('duration')) \
        .order_by('-total_time_seconds')[:5]

    # Convert seconds -> hours/minutes for display
    leaderboard = []
    for entry in leaderboard_raw:
        total_seconds = entry['total_time_seconds'] or 0
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
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
    # Find the most recent session that hasn't ended yet
    active_session = StudySession.objects.filter(
        user=request.user,
        room=room,
        end_time__isnull=True
    ).order_by('-start_time').first() # Use order_by to get the most recent

    if active_session:
        active_session.end_time = timezone.now()
        # The duration should have been updated by the JS periodically
        # No need to recalculate duration based on start/end time here
        active_session.save()
        logger.info(f"User {request.user.username} ended study session {active_session.id} in room {room.name}.")
    else:
         logger.warning(f"User {request.user.username} leaving room {room.name} but no active study session found.")


    if request.user in room.members.all():
        room.members.remove(request.user)

    return redirect('room_list')

@login_required
def update_timer(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Receive duration in seconds from JS
            duration_seconds = int(data.get('duration_seconds', 0))
            room_id = data.get('room_id')

            if duration_seconds < 0:
                 return JsonResponse({'status': 'error', 'message': 'Invalid duration'}, status=400)

            room = get_object_or_404(Room, id=room_id)

            # Find the most recent active study session for this user in this room
            # An active session is one that has started but not ended
            session = StudySession.objects.filter(
                user=request.user,
                room=room,
                end_time__isnull=True
            ).order_by('-start_time').first() # Get the latest one

            if session:
                # Add the new duration to the existing session duration
                # Ensure duration is not None before adding
                session.duration = (session.duration or 0) + duration_seconds
                session.save()
                logger.debug(f"Updated session {session.id} with +{duration_seconds}s. Total: {session.duration}s")
            else:
                # No active session found, create a new one.
                # This happens when the user starts the timer for the first time
                # in this room visit.
                session = StudySession.objects.create(
                    user=request.user,
                    room=room,
                    start_time=timezone.now(),
                    duration=duration_seconds, # Initial duration
                    end_time=None # Mark as active
                )
                logger.debug(f"Created new session {session.id} with initial {duration_seconds}s.")


            # Update user's total study time in profile
            # Ensure total_study_time is not None before adding
            request.user.profile.total_study_time = (request.user.profile.total_study_time or 0) + duration_seconds
            request.user.profile.save()
            logger.debug(f"Updated user {request.user.username} profile time with +{duration_seconds}s. Total: {request.user.profile.total_study_time}s")


            return JsonResponse({'status': 'success'})
        except json.JSONDecodeError:
            logger.error("Failed to decode JSON body in update_timer.")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"An error occurred in update_timer: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

# ... (summarize_room, ask_about_summary, get_recommended_rooms, delete_room remain the same)
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

@login_required
def delete_room(request, room_id):
    if request.user.is_staff:
        room = get_object_or_404(Room, id=room_id)
        room.delete()

    return redirect('room_list')
