import os
import requests
from flask import current_app, request as flask_request

class TurnstileUtils:
    """Cloudflare Turnstile utility class for verification"""
    
    def __init__(self):
        self.site_key = os.environ.get('TURNSTILE_SITE_KEY', '')
        self.secret_key = os.environ.get('TURNSTILE_SECRET_KEY', '')
        self.enabled = os.environ.get('TURNSTILE_ENABLED', 'False').lower() == 'true'
        self.verify_url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
    
    def is_enabled(self):
        """Check if Turnstile is enabled and properly configured"""
        return self.enabled and self.site_key and self.secret_key
    
    def get_site_key(self):
        """Get the Turnstile site key for frontend usage"""
        return self.site_key if self.is_enabled() else None
    
    def verify_turnstile(self, turnstile_response):
        """Verify Turnstile response with Cloudflare"""
        if not self.is_enabled():
            return True  # Skip verification if disabled
        
        if not turnstile_response:
            return False
        
        try:
            # Get client IP for additional security
            client_ip = self._get_client_ip()
            
            # Prepare verification request
            payload = {
                'secret': self.secret_key,
                'response': turnstile_response,
                'remoteip': client_ip
            }
            
            # Send verification request to Cloudflare
            response = requests.post(self.verify_url, data=payload, timeout=10)
            result = response.json()
            
            # Log verification attempt
            current_app.logger.info(f"Turnstile verification: success={result.get('success', False)}, IP={client_ip}")
            
            return result.get('success', False)
            
        except Exception as e:
            current_app.logger.error(f"Turnstile verification error: {e}")
            return False  # Fail secure
    
    def _get_client_ip(self):
        """Get client IP address with proxy support"""
        # Check for forwarded IP (behind proxy/load balancer)
        if flask_request.headers.get('X-Forwarded-For'):
            return flask_request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif flask_request.headers.get('X-Real-IP'):
            return flask_request.headers.get('X-Real-IP')
        else:
            return flask_request.environ.get('REMOTE_ADDR', 'unknown')

# Initialize global instance
turnstile_utils = TurnstileUtils()