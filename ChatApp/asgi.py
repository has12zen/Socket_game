from channels.layers import get_channel_layer
from chat import routing
from django.core.asgi import get_asgi_application
from channels.security.websocket import AllowedHostsOriginValidator
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ChatApp.settings')
django_asgi_app = get_asgi_application()


channel_layer = get_channel_layer()
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(
                routing.websocket_urlpatterns
            ))
        )
    }
)
