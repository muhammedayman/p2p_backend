def get_client_ip(request):
    """
    Extracts the client's real IP address from the request.
    Prioritizes 'HTTP_X_REAL_IP' set by Nginx, then 'HTTP_X_FORWARDED_FOR',
    and finally 'REMOTE_ADDR'.
    """
    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    if x_real_ip:
        return x_real_ip
        
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # X-Forwarded-For can be a comma-separated list, take the first one
        ip = x_forwarded_for.split(',')[0].strip()
        return ip
        
    return request.META.get('REMOTE_ADDR')

def get_client_ip_from_scope(scope):
    """
    Extracts IP from Django Channels scope.
    """
    headers = dict(scope.get('headers', []))
    
    # Headers are bytes: b'x-real-ip'
    x_real_ip = headers.get(b'x-real-ip')
    if x_real_ip:
        return x_real_ip.decode('utf-8')
        
    x_forwarded_for = headers.get(b'x-forwarded-for')
    if x_forwarded_for:
        return x_forwarded_for.decode('utf-8').split(',')[0].strip()
        
    # client is (host, port) tuple
    client = scope.get('client')
    if client:
        return client[0]
        
    return None
