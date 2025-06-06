from django.urls import path
from . import views
from ai import views as ai_views

urlpatterns = [
    path('', views.room_list, name='room_list'),
    path('create/', views.create_room, name='create_room'),
    path('<uuid:room_id>/', views.room_detail, name='room_detail'),
    path('<uuid:room_id>/leave/', views.leave_room, name='leave_room'),
    path('update-timer/', views.update_timer, name='update_timer'),
    path('<uuid:room_id>/summarize/', views.summarize_room, name='summarize_room'),
    path('<uuid:room_id>/ask/', views.ask_about_summary, name='ask_about_summary'),
    path('rooms/<int:room_id>/delete/', views.delete_room, name='delete_room'),
    path('<uuid:room_id>/clear_doubts/', ai_views.clear_doubts_handler, name='clear_doubts_handler'),
]