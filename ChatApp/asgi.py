import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ChatApp.settings')
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()
from chat import routing

from channels.layers import get_channel_layer

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
