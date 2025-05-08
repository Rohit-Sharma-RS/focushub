from django.urls import path
from . import views

urlpatterns = [
    path('', views.room_list, name='room_list'),
    path('create/', views.create_room, name='create_room'),
    path('<uuid:room_id>/', views.room_detail, name='room_detail'),
    path('<uuid:room_id>/leave/', views.leave_room, name='leave_room'),
    path('update-timer/', views.update_timer, name='update_timer'),
]