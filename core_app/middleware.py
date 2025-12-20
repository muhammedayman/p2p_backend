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
        log_data = f'REQUEST:{request.method} {request.get_full_path()} {request.GET}  Body: {body} Headers: {headers}\n'
        
        logger.info(log_data)

    def log_response(self, request, response, duration):
        log_data = f'RESPONSE: {request.method} {request.get_full_path()} {response.content} {response.status_code} Duration: {duration:.2f}s \n'
        logger.info(log_data)
