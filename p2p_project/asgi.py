import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'p2p_project.settings')

# Setup Django BEFORE importing apps that use models
django.setup()

# Now import routing (which imports consumers that use models)
from core_app import routing

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": URLRouter(
        routing.websocket_urlpatterns
    ),
})

# --- DEBUG: Wrap application to log ASGI events ---
import logging
# Use core_app logger because settings.py only routes this logger to server.logs
logger = logging.getLogger('core_app')

class ASGIDebugMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'websocket':
            logger.info(f"[ASGI DEBUG] Connection Attempt: Path={scope.get('path')} Client={scope.get('client')}")

        async def wrapped_receive():
            event = await receive()
            if scope['type'] == 'websocket':
                if event['type'] == 'websocket.connect':
                    logger.info(f"[ASGI DEBUG] Received CONNECT")
                elif event['type'] == 'websocket.receive':
                    logger.info(f"[ASGI DEBUG] Received DATA: {event.get('text', '')[:50]}...")
                elif event['type'] == 'websocket.disconnect':
                    logger.info(f"[ASGI DEBUG] Received DISCONNECT: {event}")
            return event

        async def wrapped_send(event):
            if scope['type'] == 'websocket':
                 if event['type'] == 'websocket.accept':
                     logger.info(f"[ASGI DEBUG] Sending ACCEPT")
                 elif event['type'] == 'websocket.close':
                     logger.info(f"[ASGI DEBUG] Sending CLOSE")
            await send(event)

        await self.app(scope, wrapped_receive, wrapped_send)

application = ASGIDebugMiddleware(application)
