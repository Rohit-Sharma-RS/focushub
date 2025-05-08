# ai/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('summarize/', views.summarize_chat, name='summarize_chat'),
    path('followup/', views.followup_question, name='followup_question'),
]