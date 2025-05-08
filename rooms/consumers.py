import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Message
from django.contrib.auth.models import User
from ai.sentiment import analyze_sentiment
from ai.motivational import get_motivational_response

class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'room_{self.room_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        username = data['username']
        
        # Analyze sentiment
        mood_score = analyze_sentiment(message)
        
        # Get motivational response if score is below threshold
        motivational_message = None
        if mood_score < 0.3:  # Negative sentiment threshold
            motivational_message = get_motivational_response(mood_score)
        
        # Save message
        await self.save_message(username, message, mood_score)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': username,
                'mood_score': mood_score,
                'motivational_message': motivational_message
            }
        )

    async def chat_message(self, event):
        message = event['message']
        username = event['username']
        mood_score = event['mood_score']
        motivational_message = event.get('motivational_message')

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'username': username,
            'mood_score': mood_score,
            'motivational_message': motivational_message
        }))

    @database_sync_to_async
    def save_message(self, username, message, mood_score):
        user = User.objects.get(username=username)
        room = Room.objects.get(id=self.room_id)
        Message.objects.create(
            user=user,
            room=room,
            content=message,
            mood_score=mood_score
        )