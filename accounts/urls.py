from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='accounts/logout.html'), name='logout'),
    path('profile/', views.profile, name='profile'),
    
    # New URL for viewing other users' profiles by their username
    path('profile/<str:username>/', views.view_profile, name='view_profile'),
    
    # New URL to handle the follow/unfollow action
    path('profile/<str:username>/toggle_follow/', views.toggle_follow, name='toggle_follow'),    
    path('update-streak/', views.update_streak, name='update_streak'),
]