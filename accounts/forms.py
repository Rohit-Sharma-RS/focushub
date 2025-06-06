# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import re

class SignupForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes and placeholders to password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
        
        # Customize error messages
        self.fields['username'].error_messages = {
            'required': 'Username is required.',
            'invalid': 'Username contains invalid characters.',
        }
        self.fields['email'].error_messages = {
            'required': 'Email address is required.',
            'invalid': 'Please enter a valid email address.',
        }
        self.fields['password1'].error_messages = {
            'required': 'Password is required.',
        }
        self.fields['password2'].error_messages = {
            'required': 'Please confirm your password.',
        }
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Check if username contains only alphanumeric characters and underscores
            if not re.match(r'^[a-zA-Z0-9_]+$', username):
                raise ValidationError('Username can only contain letters, numbers, and underscores.')
            
            # Check if username is too short
            if len(username) < 3:
                raise ValidationError('Username must be at least 3 characters long.')
            
            # Check if username already exists
            if User.objects.filter(username=username).exists():
                raise ValidationError('This username is already taken. Please choose another one.')
        
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Check if email already exists
            if User.objects.filter(email=email).exists():
                raise ValidationError('An account with this email address already exists.')
        
        return email
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if password1:
            # Custom password validation
            if len(password1) < 8:
                raise ValidationError('Password must be at least 8 characters long.')
            
            if password1.isdigit():
                raise ValidationError('Password cannot be entirely numeric.')
            
            if not re.search(r'[A-Za-z]', password1):
                raise ValidationError('Password must contain at least one letter.')
        
        return password1
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2:
            if password1 != password2:
                raise ValidationError('The two password fields must match.')
        
        return password2


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Customize error messages
        self.fields['username'].error_messages = {
            'required': 'Username is required.',
        }
        self.fields['password'].error_messages = {
            'required': 'Password is required.',
        }
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            # Check if user exists
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise ValidationError('No account found with this username. Please check your username or sign up for a new account.')
            
            # Let the parent class handle password validation
            try:
                super().clean()
            except ValidationError:
                # If authentication fails, provide a clear error message
                raise ValidationError('Incorrect password. Please try again.')
        
        return self.cleaned_data