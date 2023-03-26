from channels.routing import ProtocolTypeRouter, URLRouter
from chat import routing
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import os
from django.core.asgi import get_asgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ChatApp.settings')

from channels.layers import get_channel_layer

channel_layer = get_channel_layer()
application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(
                routing.websocket_urlpatterns
            ))
        )
    }
)
