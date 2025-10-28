"""
Middleware to log all requests and responses.
Uses a logger configured by the name of django.request
to log all requests and responses according to configuration
specified for django.request.
"""
import json
# import json
import logging
import socket
import time

from django.utils.deprecation import MiddlewareMixin

request_logger = logging.getLogger('django.request')


class RequestLogMiddleware(MiddlewareMixin):
    """Request Logging Middleware."""

    def __init__(self, *args, **kwargs):
            """Constructor method."""
            super().__init__(*args, **kwargs)

    def process_request(self, request):
        """Set Request Start Time to measure time taken to service request."""
        if request.method in ['POST', 'PUT', 'PATCH']:
            request.req_body = request.body
        if str(request.get_full_path()).startswith('/v1/'):
            request.start_time = time.time()

    def extract_log_info(self, request, response=None, exception=None):
        from django.utils.encoding import force_text
        """Extract appropriate log info from requests/responses/exceptions."""
        log_data = {
            'remote_address': request.META['REMOTE_ADDR'],
            'server_hostname': socket.gethostname(),
            'request_method': request.method,
            'request_path': request.get_full_path(),
            'run_time': time.time() - request.start_time,
        }
        if request.method in ['PUT', 'POST', 'PATCH']:
            try:
                log_data['request_body'] = json.loads(
                    force_text(request.req_body, 'utf-8'))
            except:
                log_data['request_body'] = {'message': "Multi-Part Data"}
            if response:
                if response['content-type'] == 'application/json':
                    response_body = response.content
                    log_data['response_body'] = response_body
        return log_data

    def process_response(self, request, response):
        """Log data using logger."""
        if request.method != 'GET':
            if str(request.get_full_path()).startswith('/v1/'):
                log_data = self.extract_log_info(request=request,
                                                 response=response)
                request_logger.info(msg='', extra=log_data)
        return response

    def process_exception(self, request, exception):
        """Log Exceptions."""
        try:
            raise exception
        except Exception:
            request_logger.exception(msg="Unhandled Exception")
        return exception