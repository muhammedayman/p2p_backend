import logging
import time
import json

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        
        # Read request body
        try:
            body = request.body.decode('utf-8')
        except Exception:
            body = '<binary data or decode error>'
            
        # Log Request
        self.log_request(request, body)

        response = self.get_response(request)

        duration = time.time() - start_time
        
        # Log Response
        self.log_response(request, response, duration)

        return response

    def log_request(self, request, body):
        headers = dict(request.headers)
        log_data = {
            "type": "REQUEST",
            "method": request.method,
            "path": request.get_full_path(),
            "params": dict(request.GET),
            "headers": headers,
            "body": body,
        }
        logger.info(json.dumps(log_data))

    def log_response(self, request, response, duration):
        log_data = {
            "type": "RESPONSE",
            "method": request.method,
            "path": request.get_full_path(),
            "status_code": response.status_code,
            "duration_seconds": duration,
        }
        logger.info(json.dumps(log_data))
