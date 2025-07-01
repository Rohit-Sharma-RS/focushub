import os
import django

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'focushub.settings')

# Initialize Django before importing any models or apps
django.setup()

# Now it's safe to import the rest
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import rooms.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            rooms.routing.websocket_urlpatterns
        )
    ),
})

# from django.contrib.auth import get_user_model
# from django.core.management import call_command

# try:
#     call_command("migrate", interactive=False)
#     print("✅ Ran migrate from asgi.py")
    
#     User = get_user_model()
#     if not User.objects.filter(username="admin").exists():
#         User.objects.create_superuser("admin", "admin@example.com", "admin12369")
#         print("✅ Superuser created")
# except Exception as e:
#     print(f"⚠️ Migration or superuser creation failed: {e}")
